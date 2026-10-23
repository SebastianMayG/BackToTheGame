"""Chat Q&A agent: answers a viewer's question using only the match-data tools, then passes the guard."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from matchvoice.agents.guard import check_text
from matchvoice.agents.schema import Answer
from matchvoice.agents.toolloop import run_with_tools
from matchvoice.models import AskRequest, AskResponse
from matchvoice.tools.match_tools import TOOLS, MatchContext

AGENT_NAME = "chat_qa"
MAX_ATTEMPTS = 2

INSTRUCTIONS = """\
You are the match assistant of a live football broadcast. A viewer asks a question about the match they
are watching. The match is synthetic, with fictional clubs and players.

Rules:
1. ALWAYS get your facts with the tools. Never answer from memory or guess.
2. Answer ONLY with what the tool results say. The tools already hide everything the viewer has not seen yet.
3. Use ONLY numbers, team names and player names that appear in the tool results. Never invent or compute new ones.
4. If the tools cannot answer (no data, or the question is not about this match), say so briefly and suggest
   something you can answer. Do not make up an answer.
5. If a tool returns an error, read it and call the tool again with the fix (for example add the team).
6. Reply in the language given in `language`, in 1 to 3 short sentences that sound natural read aloud.
   No emojis, no markdown.
7. `event_ids`: ids of the events or moments that back your answer, copied from the tool results (may be empty).
8. If `previous_attempt_errors` is present, your last answer broke the rules: fix exactly those problems.
"""

FALLBACK = {
    "en": "I couldn't back that up with the match data. Try asking about the score, a player or the key moments.",
    "es": "No pude respaldar eso con los datos del partido. Pregunta por el marcador, un jugador o los momentos clave.",
}

ID = re.compile(r'"(?:id|player_id)":\s*"([^"]+)"|"event_ids":\s*\[([^\]]*)\]')


def known_ids(results: list[dict[str, Any]]) -> set[str]:
    """Every event, moment and player id that appears in the tool results."""
    ids: set[str] = set()
    for single, many in ID.findall(json.dumps(results, ensure_ascii=False)):
        if single:
            ids.add(single)
        ids.update(i.strip().strip('"') for i in many.split(",") if i.strip())
    return ids


def ask(req: AskRequest, seed: int) -> AskResponse:
    ctx = MatchContext.load(seed, req.home, req.away, req.until_minute)
    started = time.perf_counter()
    meta = ctx.match.meta
    fav = next((c.short_name for c in (meta.home, meta.away) if c.id == req.club), None)
    base = {"question": req.question, "language": req.lang, "now_minute": int(req.until_minute), "favourite_team": fav}
    feedback: str | None = None
    used: list[str] = []
    attempts = 0
    for _ in range(MAX_ATTEMPTS):
        attempts += 1
        data = dict(base, **({"previous_attempt_errors": feedback} if feedback else {}))
        payload = json.dumps(data, ensure_ascii=False)
        answer, results, used = run_with_tools(INSTRUCTIONS, payload, list(TOOLS), ctx, Answer)
        if answer is None or not answer.answer.strip():
            feedback = "empty answer"
            continue
        problems = check_text(answer.answer, {"facts": results, "players": [], "clock": ""})
        if not problems:
            known = known_ids(results)
            ids = [i for i in answer.event_ids if i in known][:8]
            latency = round((time.perf_counter() - started) * 1000)
            return AskResponse(
                answer=answer.answer.strip(), event_ids=ids, tools_used=used, attempts=attempts, latency_ms=latency
            )
        feedback = "; ".join(problems)
    latency = round((time.perf_counter() - started) * 1000)
    return AskResponse(
        answer=FALLBACK[req.lang], source="fallback", tools_used=used, attempts=attempts, latency_ms=latency
    )
