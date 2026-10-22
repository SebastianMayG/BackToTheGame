"""Hand-off chain: key moment -> Explainer -> Commentator -> CommentaryLine for the UI.

Each agent is checked by the grounding guard. A failed check retries once with the errors as
feedback; if it fails again, the template headline is used instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from matchvoice.agents.commentator import commentate
from matchvoice.agents.explainer import explain
from matchvoice.agents.guard import check_texts
from matchvoice.agents.schema import Commentary, Explanation
from matchvoice.models import CommentaryLine, Moment

MAX_ATTEMPTS = 2  # first try + one retry with feedback


@dataclass
class MomentResult:
    lines: list[CommentaryLine]
    explanation: Explanation | None = None
    source: str = "ai"  # "ai" or "template" (fallback)
    attempts: dict[str, int] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


def _explanation_texts(e: Explanation) -> list[str]:
    return [e.why, e.tactical_angle, *e.key_numbers]


def _fallback(moment: Moment, langs: list[str]) -> list[CommentaryLine]:
    level = 1 if moment.importance >= 0.75 else 2
    return [
        CommentaryLine(
            id=f"tpl-{moment.id}-{lang}",
            moment_id=moment.id,
            elapsed=moment.elapsed,
            clock=moment.clock,
            speaker="narrator",
            level=level,
            lang=lang,
            text=moment.headline[lang],
            source="template",
        )
        for lang in langs
        if moment.headline.get(lang)
    ]


def narrate_moment(
    moment: Moment,
    langs: list[str] | None = None,
    recent: list[str] | None = None,
) -> MomentResult:
    """Run both agents on one key moment, with guard + retry + template fallback."""
    langs = langs or ["en", "es"]
    data = moment.model_dump()
    attempts = {"explainer": 0, "commentator": 0}

    explanation: Explanation | None = None
    feedback = None
    for _ in range(MAX_ATTEMPTS):
        attempts["explainer"] += 1
        candidate = explain(data, feedback)
        problems = check_texts(_explanation_texts(candidate), data)
        if not problems:
            explanation = candidate
            break
        feedback = "; ".join(problems)
    if explanation is None:
        return MomentResult(_fallback(moment, langs), None, "template", attempts, problems)

    commentary: Commentary | None = None
    feedback = None
    for _ in range(MAX_ATTEMPTS):
        attempts["commentator"] += 1
        candidate = commentate(data, explanation, langs, recent, feedback)
        problems = check_texts([ln.text for ln in candidate.lines], data)
        if not problems:
            commentary = candidate
            break
        feedback = "; ".join(problems)
    if commentary is None:
        return MomentResult(_fallback(moment, langs), explanation, "template", attempts, problems)

    level = 1 if moment.importance >= 0.75 else 2
    lines = [
        CommentaryLine(
            id=f"ai-{moment.id}-{i}",
            moment_id=moment.id,
            elapsed=moment.elapsed,
            clock=moment.clock,
            speaker=ln.speaker,
            level=level,
            lang=ln.lang,
            text=ln.text,
            emotion=ln.emotion,
            source="ai",
        )
        for i, ln in enumerate(commentary.lines)
    ]
    return MomentResult(lines, explanation, "ai", attempts)
