"""Recapper agent: half-time, full-time and "what did I miss?" summaries, built only from a brief of facts."""

from __future__ import annotations

import json

from matchvoice.agents.client import model_deployment, project_client
from matchvoice.agents.schema import RecapText
from matchvoice.engine.analyst import Analyst
from matchvoice.engine.recap import key_moments
from matchvoice.models import Lang, Side

AGENT_NAME = "recapper"

INSTRUCTIONS = """\
You are the Recapper of a live football broadcast. You receive a BRIEF as JSON: the kind of recap
(half_time, full_time or catch_up), the language, the score, the key moments, team stats, and sometimes
the player of the match and the viewer's favourite team.

Rules:
1. Write in the language given in `language`. Natural, warm, like a broadcaster, not a stat sheet.
2. Use ONLY numbers, team names and player names that appear in the BRIEF. Never invent or estimate any.
   Refer to teams by the short names in the BRIEF (never a full club name).
   Do not add, subtract, round or convert numbers, and quote minutes exactly as the `clock` of a key moment
   (say "around the 80th minute" only if a clock says so).
3. Say what each stat is in the words of its key (xg = expected goals, shots_on_target, possession_pct, ...).
4. half_time: the score, how the half went, one or two numbers. full_time: the result, the story of the
   match, the player of the match. catch_up: what happened since `since_minute`, then the current score.
5. If `favourite_team` is present, add one sentence about that team.
6. 2 to 4 short paragraphs, 1-2 sentences each. No bullet lists, no emojis, no markdown.
7. Do not claim tactics or causes that the key moments do not state.
8. If `previous_attempt_errors` is present, your last answer broke the rules: fix exactly those problems.
9. Reply with the JSON object only.
"""


def build_brief(a: Analyst, kind: str, lang: Lang, fav_side: Side | None = None, since: float = 0.0) -> dict:
    """The only facts the Recapper may use. The guard checks its text against this same dict."""
    snap = a.snapshot()
    short = {"home": a.meta.home.short_name, "away": a.meta.away.short_name}
    pick = ("xg", "shots", "shots_on_target", "possession_pct", "pass_accuracy")
    brief: dict = {
        "kind": kind,
        "language": lang,
        "minute": int(a.elapsed // 60),
        "home": short["home"],
        "away": short["away"],
        "score": {short["home"]: a.score.home, short["away"]: a.score.away},
        "key_moments": [
            {"clock": m.clock, "team": short.get(m.team or "", ""), "what": m.headline.get(lang, "")}
            for m in key_moments(a.moments, since, 6 if kind == "catch_up" else 4)
        ],
        "stats": {
            short["home"]: {k: getattr(snap.home, k) for k in pick},
            short["away"]: {k: getattr(snap.away, k) for k in pick},
        },
    }
    if kind == "catch_up":
        brief["since_minute"] = int(since // 60)
    elif snap.top_players:
        top = snap.top_players[0]
        brief["player_of_the_match"] = {"name": top.player.name, "rating": top.rating}
    if fav_side:
        brief["favourite_team"] = short[fav_side]
    return brief


def build_input(brief: dict, feedback: str | None = None) -> str:
    data = dict(brief)
    if feedback:
        data["previous_attempt_errors"] = feedback
    return json.dumps(data, ensure_ascii=False)


def recap(brief: dict, feedback: str | None = None) -> RecapText:
    """Ask the model to write the recap for one brief."""
    with project_client() as project, project.get_openai_client() as openai:
        response = openai.responses.parse(
            model=model_deployment(),
            instructions=INSTRUCTIONS,
            input=build_input(brief, feedback),
            text_format=RecapText,
        )
        return response.output_parsed
