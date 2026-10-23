"""Runs the AI crew next to a live stream without blocking it.

Key moments are handed to the Explainer and Commentator in worker threads. Finished results are
collected by the stream, which emits them as `commentary` (source "ai") and `crew_status` events.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from matchvoice.agents.client import load_env
from matchvoice.agents.pipeline import MomentResult, ai_recap, narrate_moment
from matchvoice.engine.analyst import Analyst
from matchvoice.models import CrewStatus, Lang, Moment, Recap, Side

log = logging.getLogger(__name__)

MIN_IMPORTANCE = 0.5  # below this, moments keep their template line...
SPICE_IMPORTANCE = 0.4  # ...except an occasional smaller play, so the broadcast never goes flat
SPICE_GAP = 240.0  # match seconds without an AI line before a smaller play gets one
MAX_FAILURES = 3  # consecutive failures before the crew goes to degraded mode
CONCURRENT_CALLS = 2  # per stream, so a burst of moments does not flood the model
EXCLUDED = {"half_time", "full_time"}  # the Recapper handles these
FINISH_TIMEOUT = 20.0
RECAP_TIMEOUT = 15.0  # the stream waits this long for the Recapper at half time and full time

_active_streams = 0


def is_configured() -> bool:
    load_env()
    return bool(os.environ.get("FOUNDRY_PROJECT_ENDPOINT") and os.environ.get("FOUNDRY_MODEL_DEPLOYMENT"))


def max_ai_streams() -> int:
    load_env()
    try:
        return int(os.environ.get("MAX_AI_STREAMS", "3"))
    except ValueError:
        return 3


def _statuses(moment_id: str, r: MomentResult) -> list[CrewStatus]:
    explainer_ok = r.explanation is not None
    commentator_ran = r.attempts.get("commentator", 0) > 0
    return [
        CrewStatus(
            agent="explainer",
            moment_id=moment_id,
            status="ok" if explainer_ok else "fallback",
            attempts=r.attempts.get("explainer", 0),
            latency_ms=r.latency_ms.get("explainer"),
            problems=[] if explainer_ok else r.problems,
        ),
        CrewStatus(
            agent="commentator",
            moment_id=moment_id,
            status=("ok" if r.source == "ai" else "fallback") if commentator_ran else "skipped",
            attempts=r.attempts.get("commentator", 0),
            latency_ms=r.latency_ms.get("commentator"),
            problems=r.problems if explainer_ok and r.source != "ai" else [],
        ),
    ]


class LiveCrew:
    """One per SSE connection. Use as a context manager so the stream slot is always released."""

    def __init__(self, lang: Lang, enabled: bool) -> None:
        self.lang = lang
        self.enabled = enabled
        self.reason = ""
        self.failures = 0
        self.recent: list[str] = []
        self._last_ai = -1e9  # match time of the last moment sent to the agents
        self._tasks: set[asyncio.Task[None]] = set()
        self._out: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        self._slots = asyncio.Semaphore(CONCURRENT_CALLS)
        self._holds_stream = False

    def __enter__(self) -> LiveCrew:
        global _active_streams
        if self.enabled:
            if not is_configured():
                self.enabled, self.reason = False, "Foundry is not configured"
            elif _active_streams >= max_ai_streams():
                self.enabled, self.reason = False, "too many AI streams (MAX_AI_STREAMS)"
            else:
                _active_streams += 1
                self._holds_stream = True
        return self

    def __exit__(self, *exc: Any) -> None:
        global _active_streams
        for t in self._tasks:
            t.cancel()
        if self._holds_stream:
            _active_streams -= 1
            self._holds_stream = False

    def _emit_status(self, moment_id: str, status: str, problems: list[str] | None = None) -> None:
        for agent in ("explainer", "commentator"):
            st = CrewStatus(agent=agent, moment_id=moment_id, status=status, problems=problems or [])  # type: ignore[arg-type]
            self._out.put_nowait(("crew_status", st.model_dump_json()))

    def submit(self, moment: Moment) -> None:
        if not self.enabled or moment.type in EXCLUDED or moment.importance < SPICE_IMPORTANCE:
            return
        if moment.importance < MIN_IMPORTANCE and moment.elapsed - self._last_ai < SPICE_GAP:
            return  # a small play only gets the AI when the broadcast has been quiet for a while
        if self.failures >= MAX_FAILURES:
            self._emit_status(moment.id, "degraded")
            return
        self._last_ai = moment.elapsed
        task = asyncio.create_task(self._run(moment))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, moment: Moment) -> None:
        async with self._slots:
            try:
                result = await asyncio.to_thread(narrate_moment, moment, [self.lang], list(self.recent))
            except Exception as exc:  # network, auth, quota: the template line is already on screen
                log.warning("AI crew failed on %s: %s", moment.id, exc)
                self.failures += 1
                self._emit_status(moment.id, "error", [str(exc)[:200]])
                return
        self.failures = 0 if result.source == "ai" else self.failures + 1
        if result.source == "ai":
            for line in result.lines:
                self.recent.append(line.text)
                self._out.put_nowait(("commentary", line.model_dump_json()))
        for st in _statuses(moment.id, result):
            self._out.put_nowait(("crew_status", st.model_dump_json()))

    async def recap(self, analyst: Analyst, kind: str, fav_side: Side | None) -> Recap | None:
        """AI recap for half time or full time, or None to keep the template one."""
        if not self.enabled or self.failures >= MAX_FAILURES:
            return None
        moment_id = f"recap-{kind}"
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(ai_recap, analyst, kind, self.lang, fav_side), RECAP_TIMEOUT
            )
        except Exception as exc:  # includes the timeout
            log.warning("Recapper failed on %s: %s", kind, exc)
            self.failures += 1
            problems = [str(exc)[:200] or "timeout"]
            status = CrewStatus(agent="recapper", moment_id=moment_id, status="error", problems=problems)
            self._out.put_nowait(("crew_status", status.model_dump_json()))
            return None
        ok = result.recap.source == "ai"
        self.failures = 0 if ok else self.failures + 1
        status = CrewStatus(
            agent="recapper",
            moment_id=moment_id,
            status="ok" if ok else "fallback",
            attempts=result.attempts,
            latency_ms=result.latency_ms,
            problems=[] if ok else result.problems,
        )
        self._out.put_nowait(("crew_status", status.model_dump_json()))
        return result.recap if ok else None

    def drain(self) -> list[tuple[str, str]]:
        """Results that finished since the last call, as (event name, json) pairs."""
        items = []
        while not self._out.empty():
            items.append(self._out.get_nowait())
        return items

    async def finish(self) -> list[tuple[str, str]]:
        """Wait for calls still in flight (bounded), then return what they produced."""
        if self._tasks:
            await asyncio.wait(self._tasks, timeout=FINISH_TIMEOUT)
        return self.drain()
