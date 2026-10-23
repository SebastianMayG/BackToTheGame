"""Match-data tools. One implementation, two consumers: the MCP server and the Q&A / Analyst Query agents.

Every tool reads the match only up to `until_minute`, so an answer can never spoil what the viewer has
not reached yet. Tools return plain dicts with event ids, which is the evidence the agents must cite.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from matchvoice.engine.analyst import Analyst
from matchvoice.engine.generator import generate_match
from matchvoice.models import Match, MatchEvent, PlayerStats, Side

MAX_EVENTS = 30


@lru_cache(maxsize=16)
def _match(seed: int, home: str, away: str) -> Match:
    return generate_match(seed, home, away)


@dataclass
class MatchContext:
    match: Match
    analyst: Analyst
    until: float  # seconds of play the viewer has reached

    @classmethod
    def load(cls, seed: int, home: str, away: str, until_minute: float | None = None) -> MatchContext:
        match = _match(seed, home, away)
        until = float("inf") if until_minute is None else until_minute * 60
        analyst = Analyst(match.meta)
        for ev in match.events:
            if ev.elapsed > until:
                break
            analyst.process(ev)
        return cls(match, analyst, until)

    @property
    def events(self) -> list[MatchEvent]:
        return [e for e in self.match.events if e.elapsed <= self.until]

    def short(self, side: Side | None) -> str | None:
        if side is None:
            return None
        meta = self.match.meta
        return (meta.home if side == "home" else meta.away).short_name

    def side(self, team: str | None) -> Side | None:
        """Accepts home/away, a club id (NVR) or a short name (Rovers)."""
        if not team:
            return None
        t = team.strip().lower()
        meta = self.match.meta
        for side, club in (("home", meta.home), ("away", meta.away)):
            if t in (side, club.id.lower(), club.short_name.lower(), club.name.lower()):
                return side  # type: ignore[return-value]
        raise ValueError(f"unknown team '{team}'. Use home, away, {meta.home.id} or {meta.away.id}")

    def players(self) -> list[dict[str, Any]]:
        meta = self.match.meta
        out = []
        for side, club in (("home", meta.home), ("away", meta.away)):
            out += [
                {
                    "id": p.id,
                    "name": p.name,
                    "number": p.number,
                    "position": p.position,
                    "team": club.short_name,
                    "side": side,
                }
                for p in club.squad
            ]
        return out


def _find_players(ctx: MatchContext, query: str, team: str | None = None) -> list[dict[str, Any]]:
    q = query.strip().lower().lstrip("#")
    side = ctx.side(team)
    found = []
    for p in ctx.players():
        if side and p["side"] != side:
            continue
        if q in (p["id"].lower(), str(p["number"])) or q in p["name"].lower():
            found.append(p)
    return found


def _one_player(ctx: MatchContext, query: str, team: str | None = None) -> dict[str, Any]:
    found = _find_players(ctx, query, team)
    if not found:
        raise ValueError(f"no player matches '{query}'")
    if len(found) > 1:
        names = ", ".join(f"{p['name']} ({p['team']} #{p['number']}, id {p['id']})" for p in found[:6])
        raise ValueError(f"'{query}' is ambiguous: {names}. Pass the id or add the team")
    return found[0]


def _stats_of(ctx: MatchContext, player_id: str) -> PlayerStats | None:
    return next((s for s in ctx.analyst.player_stats() if s.player.id == player_id), None)


def _event_summary(ctx: MatchContext, e: MatchEvent) -> dict[str, Any]:
    data = {k: v for k, v in e.data.items() if isinstance(v, (int, float, str)) and not isinstance(v, bool)}
    return {
        "id": e.id,
        "clock": e.clock.display,
        "type": e.type,
        "team": ctx.short(e.team),
        "player": e.player.name if e.player else None,
        "player_id": e.player.id if e.player else None,
        "data": dict(list(data.items())[:6]),
    }


# ----------------------------------------------------------------------------- the tools


def get_match_state(ctx: MatchContext) -> dict[str, Any]:
    a, meta = ctx.analyst, ctx.match.meta
    last = ctx.events[-1] if ctx.events else None
    snap = a.snapshot()
    return {
        "home": meta.home.short_name,
        "away": meta.away.short_name,
        "clock": last.clock.display if last else "00:00",
        "period": last.period if last else 1,
        "score": {meta.home.short_name: a.score.home, meta.away.short_name: a.score.away},
        "possession_pct": {
            meta.home.short_name: snap.home.possession_pct,
            meta.away.short_name: snap.away.possession_pct,
        },
        "rhythm": a.rhythm(),
        "momentum_toward": ctx.short("home" if snap.momentum > 0 else "away")
        if abs(snap.momentum) > 0.15
        else "balanced",
    }


def get_team_stats(ctx: MatchContext, team: str) -> dict[str, Any]:
    side = ctx.side(team)
    snap = ctx.analyst.snapshot()
    stats = snap.home if side == "home" else snap.away
    return {"team": ctx.short(side), **stats.model_dump()}


def find_player(ctx: MatchContext, query: str, team: str | None = None) -> dict[str, Any]:
    return {"players": _find_players(ctx, query, team)[:8]}


def get_player_stats(ctx: MatchContext, player: str, team: str | None = None) -> dict[str, Any]:
    p = _one_player(ctx, player, team)
    s = _stats_of(ctx, p["id"])
    return {"player": p, "stats": s.model_dump(exclude={"player", "team"}) if s else "has not touched the ball yet"}


def find_events(
    ctx: MatchContext,
    type: str | None = None,
    team: str | None = None,
    player: str | None = None,
    period: int | None = None,
    from_minute: float | None = None,
    to_minute: float | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Events matching a filter. `total` counts every match, `events` returns the latest `limit` of them."""
    side = ctx.side(team)
    pid = _one_player(ctx, player, team)["id"] if player else None
    hits = [
        e
        for e in ctx.events
        if (not type or e.type == type)
        and (not side or e.team == side)
        and (not pid or (e.player and e.player.id == pid))
        and (not period or e.period == period)
        and (from_minute is None or e.elapsed >= from_minute * 60)
        and (to_minute is None or e.elapsed <= to_minute * 60)
    ]
    shown = hits[-max(1, min(limit, MAX_EVENTS)) :]
    return {"total": len(hits), "events": [_event_summary(ctx, e) for e in shown]}


def get_key_moments(ctx: MatchContext, since_minute: float = 0, limit: int = 8) -> dict[str, Any]:
    picked = [
        m for m in ctx.analyst.moments if m.elapsed >= since_minute * 60 and m.type not in ("half_time", "full_time")
    ]
    picked = sorted(sorted(picked, key=lambda m: -m.importance)[: max(1, min(limit, 20))], key=lambda m: m.elapsed)
    return {
        "moments": [
            {
                "id": m.id,
                "clock": m.clock,
                "type": m.type,
                "team": ctx.short(m.team),
                "headline": m.headline.get("en", ""),
                "facts": m.facts,
                "event_ids": m.event_ids,
            }
            for m in picked
        ]
    }


def compare_players(ctx: MatchContext, a: str, b: str) -> dict[str, Any]:
    return {"a": get_player_stats(ctx, a), "b": get_player_stats(ctx, b)}


# ----------------------------------------------------------------------------- registry for the agents

_PLAYER = {"type": "string", "description": "Player id, name or shirt number (add `team` if only a number)"}
_TEAM = {"type": "string", "description": "home, away, a club id (e.g. NVR) or a short name (e.g. Rovers)"}

TOOLS: dict[str, dict[str, Any]] = {
    "get_match_state": {
        "fn": get_match_state,
        "description": "Score, clock, period, possession, rhythm and momentum right now.",
        "parameters": {"type": "object", "properties": {}},
    },
    "get_team_stats": {
        "fn": get_team_stats,
        "description": "Team statistics so far: goals, xg, shots, passes, possession, ppda, field tilt...",
        "parameters": {"type": "object", "properties": {"team": _TEAM}, "required": ["team"]},
    },
    "find_player": {
        "fn": find_player,
        "description": "Look a player up by name, shirt number or id. Use it to get a player id.",
        "parameters": {"type": "object", "properties": {"query": _PLAYER, "team": _TEAM}, "required": ["query"]},
    },
    "get_player_stats": {
        "fn": get_player_stats,
        "description": "Statistics of one player so far: passes, shots, xg, goals, sprints, top speed, rating...",
        "parameters": {"type": "object", "properties": {"player": _PLAYER, "team": _TEAM}, "required": ["player"]},
    },
    "find_events": {
        "fn": find_events,
        "description": (
            "Events filtered by type, team, player, period or minute range. Returns the total count and the "
            "latest events with their ids. Types: pass, carry, pressure, tackle, interception, foul, card, "
            "corner, shot, save, block, goal, substitution."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "team": _TEAM,
                "player": _PLAYER,
                "period": {"type": "integer", "enum": [1, 2]},
                "from_minute": {"type": "number"},
                "to_minute": {"type": "number"},
                "limit": {"type": "integer", "description": "How many of the latest events to return (max 30)"},
            },
        },
    },
    "get_key_moments": {
        "fn": get_key_moments,
        "description": "Key moments detected so far (goals, big chances, saves, momentum swings...) with their facts.",
        "parameters": {
            "type": "object",
            "properties": {"since_minute": {"type": "number"}, "limit": {"type": "integer"}},
        },
    },
    "compare_players": {
        "fn": compare_players,
        "description": "Side-by-side statistics of two players.",
        "parameters": {"type": "object", "properties": {"a": _PLAYER, "b": _PLAYER}, "required": ["a", "b"]},
    },
}


def call_tool(ctx: MatchContext, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run a tool for an agent. Errors come back as data so the model can correct its call."""
    spec = TOOLS.get(name)
    if spec is None:
        return {"error": f"unknown tool '{name}'"}
    try:
        return spec["fn"](ctx, **args)
    except (ValueError, TypeError) as exc:
        return {"error": str(exc)}
