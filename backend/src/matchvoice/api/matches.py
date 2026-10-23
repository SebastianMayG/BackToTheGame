"""REST and Server-Sent Events endpoints for matches."""

from __future__ import annotations

import asyncio
import csv
import io
import json
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from matchvoice.agents.live import LiveCrew, is_configured
from matchvoice.agents.pipeline import ai_recap
from matchvoice.engine.analyst import Analyst
from matchvoice.engine.clubs import all_clubs
from matchvoice.engine.generator import generate_match
from matchvoice.engine.narration import NarrationContext, narrate_event
from matchvoice.engine.recap import build_recap
from matchvoice.models import (
    Club,
    CommentaryLine,
    CrewStatus,
    Lang,
    Match,
    MatchEvent,
    MatchMeta,
    Mode,
    Moment,
    PlayerStats,
    Recap,
    Side,
    StatsSnapshot,
)

router = APIRouter(prefix="/api")

MAX_DELAY_SEC = 2.5  # dead time (goals, substitutions) is shortened on replay


@lru_cache(maxsize=32)
def get_match(seed: int, home: str, away: str) -> Match:
    try:
        return generate_match(seed, home, away)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _fav_side(meta: MatchMeta, club: str | None) -> Side | None:
    if club == meta.home.id:
        return "home"
    if club == meta.away.id:
        return "away"
    return None


def _replay(match: Match, until: float | None = None) -> Analyst:
    analyst = Analyst(match.meta)
    for ev in match.events:
        if until is not None and ev.elapsed > until:
            break
        analyst.process(ev)
    return analyst


def _pundit_line(m: Moment, lang: Lang) -> CommentaryLine | None:
    text = m.headline.get(lang)
    if not text or m.type in ("half_time", "full_time"):
        return None
    level = 1 if m.importance >= 0.7 else 2 if m.importance >= 0.4 else 3
    emotion = (
        "excited"
        if m.type in ("goal", "great_save", "rocket_shot")
        else "tense"
        if m.type in ("big_chance", "penalty_awarded", "red_card")
        else "neutral"
    )
    return CommentaryLine(
        id=f"pundit-{m.id}-{lang}",
        moment_id=m.id,
        elapsed=m.elapsed,
        clock=m.clock,
        speaker="pundit",
        level=level,  # type: ignore[arg-type]
        lang=lang,
        text=text,
        emotion=emotion,  # type: ignore[arg-type]
    )


class ClubsResponse(BaseModel):
    clubs: list[Club]


class AnalysisResponse(BaseModel):
    meta: MatchMeta
    moments: list[Moment]
    stats: StatsSnapshot
    players: list[PlayerStats]


@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "agents": "configured" if is_configured() else "not_configured"}


@router.get("/clubs", response_model=ClubsResponse)
def clubs() -> ClubsResponse:
    return ClubsResponse(clubs=list(all_clubs().values()))


@router.get("/matches/{seed}", response_model=Match)
def match(seed: int, home: str = "NVR", away: str = "KBY") -> Match:
    return get_match(seed, home, away)


@router.get("/matches/{seed}/analysis", response_model=AnalysisResponse)
def analysis(seed: int, home: str = "NVR", away: str = "KBY") -> AnalysisResponse:
    m = get_match(seed, home, away)
    a = _replay(m)
    return AnalysisResponse(meta=m.meta, moments=a.moments, stats=a.snapshot(), players=a.player_stats())


@router.get("/matches/{seed}/catchup", response_model=Recap)
def catchup(
    seed: int,
    until: float = Query(..., ge=0, description="Elapsed seconds the viewer has reached"),
    since: float = Query(0, ge=0, description="Elapsed seconds from which to summarise"),
    home: str = "NVR",
    away: str = "KBY",
    lang: Lang = "es",
    club: str | None = None,
    ai: bool = Query(False, description="Write the summary with the Recapper agent"),
) -> Recap:
    m = get_match(seed, home, away)
    a = _replay(m, until)
    fav_side = _fav_side(m.meta, club)
    if ai and is_configured():
        return ai_recap(a, "catch_up", lang, fav_side, since).recap
    return build_recap(a, "catch_up", lang, fav_side, since=since)


@router.get("/matches/{seed}/export")
def export(seed: int, home: str = "NVR", away: str = "KBY", format: Literal["csv", "json"] = "csv") -> Response:
    m = get_match(seed, home, away)
    filename = f"{m.meta.match_id}.{format}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if format == "json":
        a = _replay(m)
        body = AnalysisResponse(meta=m.meta, moments=a.moments, stats=a.snapshot(), players=a.player_stats())
        return Response(body.model_dump_json(indent=2), media_type="application/json", headers=headers)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "seq",
            "clock",
            "period",
            "type",
            "team",
            "player",
            "x",
            "y",
            "home",
            "away",
            "outcome",
            "xg",
            "speed_kmh",
            "distance",
        ]
    )
    for ev in m.events:
        d = ev.data
        writer.writerow(
            [
                ev.seq,
                ev.clock.display,
                ev.period,
                ev.type,
                ev.team or "",
                ev.player.name if ev.player else "",
                ev.location.x if ev.location else "",
                ev.location.y if ev.location else "",
                ev.score.home,
                ev.score.away,
                d.get("outcome", ""),
                d.get("xg", ""),
                d.get("speed_kmh", d.get("top_speed_kmh", "")),
                d.get("distance", d.get("distance_to_goal", "")),
            ]
        )
    return Response(buf.getvalue(), media_type="text/csv", headers=headers)


class StreamContract(BaseModel):
    """Payload of each SSE event type on /matches/{seed}/stream (documents the stream in OpenAPI)."""

    meta: MatchMeta
    match_event: MatchEvent
    pbp: CommentaryLine
    moment: Moment | None
    commentary: CommentaryLine | None
    crew_status: CrewStatus
    stats: StatsSnapshot
    recap: Recap


@router.get("/stream/contract", response_model=StreamContract)
def stream_contract() -> StreamContract:
    """A real sample of every stream payload, from the first half of match 1."""
    m = get_match(1, "NVR", "KBY")
    a = Analyst(m.meta)
    ctx = NarrationContext(meta=m.meta)
    sample_ev, sample_line, sample_moment = m.events[0], None, None
    for ev in m.events:
        moments = a.process(ev)
        line = narrate_event(ev, ctx)
        if line and sample_line is None:
            sample_ev, sample_line = ev, line
        if moments and sample_moment is None:
            sample_moment = moments[0]
        if ev.type == "period_end":
            break
    assert sample_line is not None
    return StreamContract(
        meta=m.meta,
        match_event=sample_ev,
        pbp=sample_line,
        moment=sample_moment,
        commentary=_pundit_line(sample_moment, "es") if sample_moment else None,
        crew_status=CrewStatus(agent="explainer", moment_id="m1", status="ok", attempts=1, latency_ms=1200),
        stats=a.snapshot(),
        recap=build_recap(a, "half_time", "es"),
    )


@router.get("/matches/{seed}/stream")
async def stream(
    request: Request,
    seed: int,
    home: str = "NVR",
    away: str = "KBY",
    speed: float = Query(30, ge=1, le=240, description="Replay speed: 30 plays 90 minutes in about 3"),
    lang: Lang = "es",
    mode: Mode = "fan",
    club: str | None = None,
    player: str | None = None,
    from_seq: int = Query(0, ge=0, description="Resume after this event (e.g. after switching language or mode)"),
    ai: bool = Query(False, description="Add AI commentary (Explainer + Commentator) on key moments"),
) -> EventSourceResponse:
    """Live replay as SSE: meta, match_event, pbp, moment, commentary, crew_status, stats, recap, end."""
    m = get_match(seed, home, away)
    fav_side = _fav_side(m.meta, club)
    ctx = NarrationContext(meta=m.meta, lang=lang, mode=mode, fav_side=fav_side, fav_player=player)
    try:
        resume_seq = int(request.headers.get("last-event-id", "0"))
    except ValueError:
        resume_seq = 0
    resume_seq = max(resume_seq, from_seq)

    async def events() -> AsyncIterator[dict[str, str]]:
        with LiveCrew(lang, enabled=ai) as crew:
            async for item in replay(crew):
                yield item

    async def replay(crew: LiveCrew) -> AsyncIterator[dict[str, str]]:
        analyst = Analyst(m.meta)
        yield {"event": "meta", "data": m.meta.model_dump_json()}
        if ai and not crew.enabled:
            disabled = {"agent": "crew", "status": "disabled", "reason": crew.reason}
            yield {"event": "crew_status", "data": json.dumps(disabled)}
        prev: float | None = None
        last_stats = -1e9
        for ev in m.events:
            if await request.is_disconnected():
                return
            replaying = ev.seq <= resume_seq
            if not replaying and prev is not None:
                delay = min((ev.elapsed - prev) / speed, MAX_DELAY_SEC)
                if delay > 0:
                    await asyncio.sleep(delay)
            prev = ev.elapsed
            moments = analyst.process(ev)
            if replaying:
                continue
            sid = str(ev.seq)
            for name, data in crew.drain():
                yield {"event": name, "id": sid, "data": data}
            yield {"event": "match_event", "id": sid, "data": ev.model_dump_json()}
            line = narrate_event(ev, ctx)
            if line:
                yield {"event": "pbp", "id": sid, "data": line.model_dump_json()}
            for mo in moments:
                yield {"event": "moment", "id": sid, "data": mo.model_dump_json()}
                pundit = _pundit_line(mo, lang)
                if pundit:
                    yield {"event": "commentary", "id": sid, "data": pundit.model_dump_json()}
                crew.submit(mo)
            if moments or ev.elapsed - last_stats >= 10:
                last_stats = ev.elapsed
                yield {"event": "stats", "id": sid, "data": analyst.snapshot().model_dump_json()}
            if ev.type == "period_end":
                kind = "half_time" if ev.data["period"] == 1 else "full_time"
                recap = await crew.recap(analyst, kind, fav_side) or build_recap(analyst, kind, lang, fav_side)
                yield {"event": "recap", "id": sid, "data": recap.model_dump_json()}
        for name, data in await crew.finish():
            yield {"event": name, "data": data}
        yield {"event": "end", "data": "{}"}

    return EventSourceResponse(events(), ping=15)
