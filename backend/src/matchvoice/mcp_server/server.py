"""MCP server: the match-data tools for any MCP client (GitHub Copilot, Claude Desktop, MCP Inspector).

Run it with `uv run matchvoice mcp` (stdio). Each tool takes the match (seed, home, away) and how far the
viewer has watched (`until_minute`); leave it out to read the whole match.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from matchvoice.tools import match_tools as t

mcp = MCPServer(
    "matchvoice",
    instructions=(
        "Live data of a synthetic football match (fictional clubs and players). Pass seed/home/away to pick "
        "the match and until_minute to read it only up to that minute."
    ),
)


def _ctx(seed: int, home: str, away: str, until_minute: float | None) -> t.MatchContext:
    return t.MatchContext.load(seed, home, away, until_minute)


@mcp.tool()
def get_match_state(
    seed: int = 42, home: str = "NVR", away: str = "KBY", until_minute: float | None = None
) -> dict[str, Any]:
    """Score, clock, period, possession, rhythm and momentum."""
    return t.get_match_state(_ctx(seed, home, away, until_minute))


@mcp.tool()
def get_team_stats(
    team: str, seed: int = 42, home: str = "NVR", away: str = "KBY", until_minute: float | None = None
) -> dict[str, Any]:
    """Team statistics: goals, xg, shots, passes, possession, ppda, field tilt."""
    return t.get_team_stats(_ctx(seed, home, away, until_minute), team)


@mcp.tool()
def find_player(
    query: str, team: str | None = None, seed: int = 42, home: str = "NVR", away: str = "KBY"
) -> dict[str, Any]:
    """Look a player up by name, shirt number or id."""
    return t.find_player(_ctx(seed, home, away, None), query, team)


@mcp.tool()
def get_player_stats(
    player: str,
    team: str | None = None,
    seed: int = 42,
    home: str = "NVR",
    away: str = "KBY",
    until_minute: float | None = None,
) -> dict[str, Any]:
    """Statistics of one player: passes, shots, xg, goals, sprints, top speed, rating."""
    return t.get_player_stats(_ctx(seed, home, away, until_minute), player, team)


@mcp.tool()
def find_events(
    type: str | None = None,
    team: str | None = None,
    player: str | None = None,
    period: int | None = None,
    from_minute: float | None = None,
    to_minute: float | None = None,
    limit: int = 10,
    seed: int = 42,
    home: str = "NVR",
    away: str = "KBY",
    until_minute: float | None = None,
) -> dict[str, Any]:
    """Events filtered by type, team, player, period or minute range, with the total count and event ids."""
    return t.find_events(
        _ctx(seed, home, away, until_minute), type, team, player, period, from_minute, to_minute, limit
    )


@mcp.tool()
def get_key_moments(
    since_minute: float = 0,
    limit: int = 8,
    seed: int = 42,
    home: str = "NVR",
    away: str = "KBY",
    until_minute: float | None = None,
) -> dict[str, Any]:
    """Key moments (goals, big chances, saves, momentum swings...) with their facts."""
    return t.get_key_moments(_ctx(seed, home, away, until_minute), since_minute, limit)


@mcp.tool()
def compare_players(
    a: str, b: str, seed: int = 42, home: str = "NVR", away: str = "KBY", until_minute: float | None = None
) -> dict[str, Any]:
    """Side-by-side statistics of two players."""
    return t.compare_players(_ctx(seed, home, away, until_minute), a, b)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
