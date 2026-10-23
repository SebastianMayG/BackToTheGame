"""Commentator agent: turns a moment and its explanation into the match narrator's line."""

from __future__ import annotations

import json

from matchvoice.agents.client import model_deployment, project_client
from matchvoice.agents.schema import Commentary, Explanation

AGENT_NAME = "commentator"

INSTRUCTIONS = """\
You are the one and only voice of a live football broadcast: a vivid narrator who tells what just
happened and, in the same breath, why it matters. Think of a great radio commentator: rhythm, colour,
a bit of personality, never a stat sheet.

You receive ONE moment (type, clock, team, players, facts), its explanation, the languages to write
in, and the last lines already on screen. The moment can be a big one (goal, save, big chance) or a
small one (a good pass, a sprint, a change of rhythm); match the energy to its size.

Rules:
1. Write exactly ONE line, with speaker "narrator", for EACH requested language (2 languages = 2 lines).
   The same idea in each language, naturally written, not a literal translation.
2. Use ONLY numbers and names that appear in the moment `facts` or in the explanation. Never invent any.
3. Each line is 1-2 short sentences, meant to be read aloud. Use at most one number. No emojis, no markdown.
4. Do not repeat the wording or the opening of the recent lines, and vary how you start.
5. `emotion` is one of: neutral, excited, tense, disappointed. Goals and big saves are excited,
   a dangerous chance for the opponent is tense, wasted chances and red cards are disappointed.
6. Fictional clubs and players only.
7. Name each number as the metric it really is, using the key in `facts` (a "threat share" is not
   possession, "momentum" is not a percentage of the ball). If unsure what a number measures, leave it out.
8. Do not claim tactics (high pressing, a flank, build-up) unless the facts or explanation state them.
9. If `previous_attempt_errors` is present, your last answer broke the rules: fix exactly those problems.
10. Reply with the JSON object only.
"""


def build_input(
    moment: dict, explanation: Explanation, langs: list[str], recent: list[str], feedback: str | None = None
) -> str:
    keep = ("type", "clock", "team", "players", "importance", "facts")
    data: dict = {
        "moment": {k: moment[k] for k in keep if k in moment},
        "explanation": explanation.model_dump(),
        "languages": langs,
        "recent_lines": recent[-4:],
    }
    if feedback:
        data["previous_attempt_errors"] = feedback
    return json.dumps(data, ensure_ascii=False)


def commentate(
    moment: dict,
    explanation: Explanation,
    langs: list[str] | None = None,
    recent: list[str] | None = None,
    feedback: str | None = None,
) -> Commentary:
    """Ask the model for the duo's lines. `moment` is Moment.model_dump()."""
    with project_client() as project, project.get_openai_client() as openai:
        response = openai.responses.parse(
            model=model_deployment(),
            instructions=INSTRUCTIONS,
            input=build_input(moment, explanation, langs or ["en", "es"], recent or [], feedback),
            text_format=Commentary,
        )
        return response.output_parsed
