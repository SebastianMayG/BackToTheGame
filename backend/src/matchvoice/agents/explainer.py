"""Explainer agent: says why a key moment matters, using only the evidence the Analyst found."""

from __future__ import annotations

import json

from matchvoice.agents.client import model_deployment, project_client
from matchvoice.agents.schema import Explanation

AGENT_NAME = "explainer"

INSTRUCTIONS = """\
You are the Explainer of a live football broadcast. You receive ONE key moment detected by an
analytics engine, as JSON with: type, clock, team, players, importance and facts.

Your job is to explain WHY this moment matters, in plain language a casual fan understands.

Rules:
1. Use ONLY numbers that appear in `facts`. Never invent or estimate a number, a player or a stat.
2. If a number is not in `facts`, do not mention it.
3. `why`: 1-2 sentences, what happened and why it matters for the match.
4. `tactical_angle`: 1 sentence on the tactical reading (pressing, control, momentum, chance quality).
5. `key_numbers`: 1-3 short strings copied from `facts`, like "xG 0.18" or "66.6 km/h".
6. `confidence`: 0 to 1. Lower it when `facts` is thin.
7. Fictional clubs and players only. Write in English.
8. Name each metric exactly as its key in `facts` says. A "threat share" is not possession, and a
   "momentum" value is not a percentage of the ball. If you are unsure what a number measures, leave it out.
9. Do not claim tactics (high pressing, a flank, build-up) unless `facts` or `type` states them.
10. If `previous_attempt_errors` is present, your last answer broke the rules: fix exactly those problems.
11. Reply with the JSON object only.
"""


def build_input(moment: dict, feedback: str | None = None) -> str:
    """Only send what the model needs, so the prompt stays short and cheap."""
    keep = ("type", "clock", "team", "players", "importance", "facts")
    data: dict = {k: moment[k] for k in keep if k in moment}
    if feedback:
        data["previous_attempt_errors"] = feedback
    return json.dumps(data, ensure_ascii=False)


def explain(moment: dict, feedback: str | None = None) -> Explanation:
    """Ask the model to explain one key moment. `moment` is Moment.model_dump()."""
    with project_client() as project, project.get_openai_client() as openai:
        response = openai.responses.parse(
            model=model_deployment(),
            instructions=INSTRUCTIONS,
            input=build_input(moment, feedback),
            text_format=Explanation,
        )
        return response.output_parsed
