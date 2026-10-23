from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from matchvoice.agents import analyst_query
from matchvoice.agents.qa import known_ids
from matchvoice.agents.schema import QueryPlan
from matchvoice.api import agents as agents_api
from matchvoice.main import app
from matchvoice.mcp_server.server import mcp
from matchvoice.models import AskResponse, QueryResponse
from matchvoice.tools.match_tools import TOOLS, MatchContext, call_tool

client = TestClient(app)


@pytest.fixture(scope="module")
def ctx() -> MatchContext:
    return MatchContext.load(42, "NVR", "KBY", 60)


def test_tools_never_read_past_the_viewer_minute(ctx: MatchContext) -> None:
    assert ctx.events and max(e.elapsed for e in ctx.events) <= 60 * 60
    early = MatchContext.load(42, "NVR", "KBY", 10)
    assert (
        call_tool(early, "find_events", {"type": "shot"})["total"]
        < call_tool(ctx, "find_events", {"type": "shot"})["total"]
    )


def test_team_can_be_named_in_several_ways(ctx: MatchContext) -> None:
    for name in ("home", "NVR", "Rovers", "rovers"):
        assert call_tool(ctx, "get_team_stats", {"team": name})["team"] == "Rovers"
    assert "error" in call_tool(ctx, "get_team_stats", {"team": "Barcelona"})


def test_ambiguous_shirt_number_comes_back_as_an_error_the_model_can_fix(ctx: MatchContext) -> None:
    assert "ambiguous" in call_tool(ctx, "get_player_stats", {"player": "9"})["error"]
    assert call_tool(ctx, "get_player_stats", {"player": "9", "team": "Rovers"})["player"]["id"] == "NVR-9"


def test_unknown_tool_and_bad_arguments_are_data_not_crashes(ctx: MatchContext) -> None:
    assert "error" in call_tool(ctx, "launch_missiles", {})
    assert "error" in call_tool(ctx, "get_team_stats", {"nope": 1})


def test_event_ids_in_results_are_collected_as_evidence(ctx: MatchContext) -> None:
    result = call_tool(ctx, "find_events", {"type": "shot", "limit": 3})
    ids = known_ids([result])
    assert {e["id"] for e in result["events"]} <= ids


def test_mcp_server_exposes_the_same_tools() -> None:
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == set(TOOLS)
    res = asyncio.run(mcp.call_tool("get_match_state", {"until_minute": 30}))
    assert "Rovers" in res.content[0].text


def _plan(**kw) -> QueryPlan:  # type: ignore[no-untyped-def]
    base = dict(
        understood=True, layer="shot_map", team=None, player_id=None, period=None, from_minute=None, to_minute=None
    )
    return QueryPlan(**{**base, **kw})


def test_overlay_counts_come_from_the_data(ctx: MatchContext) -> None:
    spec = analyst_query.build_overlay(ctx, _plan(team="home"), "en")
    expected = call_tool(ctx, "find_events", {"type": "shot", "team": "home", "limit": 30})["total"]
    assert spec.count == expected and spec.title.startswith("Shot map")


def test_overlay_player_sets_the_team_and_rejects_invented_ids(ctx: MatchContext) -> None:
    spec = analyst_query.build_overlay(ctx, _plan(layer="heatmap", player_id="KBY-8"), "es")
    assert spec.filter.team == "away" and "#8" in spec.title and spec.title.startswith("Mapa de calor")
    with pytest.raises(ValueError):
        analyst_query.build_overlay(ctx, _plan(player_id="XXX-99"), "en")


def test_ask_endpoint(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(agents_api, "is_configured", lambda: True)
    monkeypatch.setattr(agents_api, "run_ask", lambda req, seed: AskResponse(answer=f"seed {seed}"))
    res = client.post("/api/matches/7/ask", json={"question": "who leads?", "until_minute": 30})
    assert res.status_code == 200 and res.json()["answer"] == "seed 7"


def test_query_endpoint_and_validation(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(agents_api, "is_configured", lambda: True)
    monkeypatch.setattr(agents_api, "run_query", lambda req, seed: QueryResponse(message="ok"))
    assert client.post("/api/matches/7/query", json={"query": "shots", "until_minute": 30}).json()["message"] == "ok"
    assert client.post("/api/matches/7/query", json={"query": "shots", "until_minute": 999}).status_code == 422


def test_agents_are_503_when_not_configured(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(agents_api, "is_configured", lambda: False)
    assert client.post("/api/matches/7/ask", json={"question": "who leads?", "until_minute": 30}).status_code == 503
