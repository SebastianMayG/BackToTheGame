"""Analyst Query agent: turns a request in natural language into an OverlaySpec the pitch can draw.

The model only plans (layer, team, player, period, minutes). Code validates the plan, counts the matching
events and writes the title, so nothing shown on the pitch is invented.
"""

from __future__ import annotations

import json
import time

from matchvoice.agents.schema import QueryPlan
from matchvoice.agents.toolloop import run_with_tools
from matchvoice.models import Lang, MatchEvent, OverlayFilter, OverlaySpec, QueryRequest, QueryResponse
from matchvoice.tools.match_tools import MatchContext

AGENT_NAME = "analyst_query"
MAX_ATTEMPTS = 2
MAX_IDS = 60
HEATMAP_TYPES = {"pass", "carry", "shot", "tackle", "interception", "pressure"}

INSTRUCTIONS = """\
You are the Analyst Query agent of a football analytics tool. The analyst types a request in natural
language and you decide what the pitch should draw. The match is synthetic, with fictional clubs and players.

You choose:
- `layer`: "shot_map" (shots), "heatmap" (where a team or player was active) or "progressive_passes"
  (passes that move the ball forward). If the request is not about drawing one of these, set `understood` to false
  and leave the rest null.
- `team`: "home" or "away" (the input lists which club is which). Null for both.
- `player_id`: when the request names a player or a shirt number, call `find_player` and copy the `id` from its
  result. Never invent an id. If the shirt number exists in both teams and the team is not clear, use `team` too.
- `period`: 1 or 2 for "first half" or "second half". When you set a period, leave the minutes null unless
  the request names minutes.
- `from_minute` / `to_minute`: a minute range. `now_minute` is the current match minute, so "the last 10 minutes"
  is from_minute = now_minute - 10.

If `previous_attempt_errors` is present, your last answer was invalid: fix exactly that.
Reply with the JSON object only.
"""

LAYER_NAME = {
    "en": {"shot_map": "Shot map", "heatmap": "Heatmap", "progressive_passes": "Progressive passes"},
    "es": {"shot_map": "Mapa de tiros", "heatmap": "Mapa de calor", "progressive_passes": "Pases progresivos"},
}
HALF = {"en": {1: "1st half", 2: "2nd half"}, "es": {1: "1T", 2: "2T"}}
FALLBACK = {
    "en": "I couldn't turn that into a pitch layer. Try something like: shots by Rovers in the second half.",
    "es": "No pude convertir eso en una capa de la cancha. Prueba algo como: tiros de Rovers en el segundo tiempo.",
}
NO_EVENTS = {"en": "No events match that filter yet.", "es": "Todavía no hay eventos con ese filtro."}


def _matches(layer: str, e: MatchEvent) -> bool:
    if layer == "shot_map":
        return e.type == "shot"
    if layer == "progressive_passes":
        return e.type == "pass" and e.data.get("outcome") == "complete" and e.data.get("progressive", 0) >= 10
    return e.type in HEATMAP_TYPES


def build_overlay(ctx: MatchContext, plan: QueryPlan, lang: Lang) -> OverlaySpec:
    """Validate the plan against the data and count what it selects. Raises ValueError for a bad player id."""
    assert plan.layer is not None
    player = None
    if plan.player_id:
        player = next((p for p in ctx.players() if p["id"] == plan.player_id), None)
        if player is None:
            raise ValueError(f"player_id '{plan.player_id}' does not exist; call find_player and copy its id")
    team = plan.team or (player["side"] if player else None)
    events = [
        e
        for e in ctx.events
        if e.location
        and _matches(plan.layer, e)
        and (not team or e.team == team)
        and (not player or (e.player and e.player.id == player["id"]))
        and (not plan.period or e.period == plan.period)
        and (plan.from_minute is None or e.elapsed >= plan.from_minute * 60)
        and (plan.to_minute is None or e.elapsed <= plan.to_minute * 60)
    ]
    parts = [LAYER_NAME[lang][plan.layer]]
    if player:
        parts.append(f"#{player['number']} {player['name']}")
    elif team:
        parts.append(ctx.short(team) or "")
    if plan.period:
        parts.append(HALF[lang][plan.period])
    if plan.from_minute is not None or plan.to_minute is not None:
        lo = int(plan.from_minute) if plan.from_minute is not None else 0
        hi = (
            int(plan.to_minute)
            if plan.to_minute is not None
            else int(ctx.until // 60)
            if ctx.until != float("inf")
            else 90
        )
        parts.append(f"{max(lo, 0)}'-{hi}'")
    return OverlaySpec(
        layer=plan.layer,
        filter=OverlayFilter(
            team=team,
            player_id=player["id"] if player else None,
            period=plan.period,
            from_minute=plan.from_minute,
            to_minute=plan.to_minute,
        ),
        title=" — ".join(parts),
        count=len(events),
        event_ids=[e.id for e in events[-MAX_IDS:]],
    )


def query(req: QueryRequest, seed: int) -> QueryResponse:
    ctx = MatchContext.load(seed, req.home, req.away, req.until_minute)
    started = time.perf_counter()
    meta = ctx.match.meta
    base = {
        "request": req.query,
        "now_minute": int(req.until_minute),
        "home": {"side": "home", "id": meta.home.id, "name": meta.home.short_name},
        "away": {"side": "away", "id": meta.away.id, "name": meta.away.short_name},
    }
    feedback: str | None = None
    used: list[str] = []
    for _ in range(MAX_ATTEMPTS):
        data = dict(base, **({"previous_attempt_errors": feedback} if feedback else {}))
        plan, _results, used = run_with_tools(
            INSTRUCTIONS, json.dumps(data, ensure_ascii=False), ["find_player"], ctx, QueryPlan
        )
        if plan is None or not plan.understood or plan.layer is None:
            break
        try:
            overlay = build_overlay(ctx, plan, req.lang)
        except ValueError as exc:
            feedback = str(exc)
            continue
        latency = round((time.perf_counter() - started) * 1000)
        message = "" if overlay.count else NO_EVENTS[req.lang]
        return QueryResponse(overlay=overlay, message=message, tools_used=used, latency_ms=latency)
    latency = round((time.perf_counter() - started) * 1000)
    return QueryResponse(message=FALLBACK[req.lang], source="fallback", tools_used=used, latency_ms=latency)
