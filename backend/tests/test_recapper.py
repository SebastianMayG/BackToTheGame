from __future__ import annotations

import pytest

from matchvoice.agents import pipeline
from matchvoice.agents.recapper import build_brief
from matchvoice.agents.schema import RecapText
from matchvoice.engine.analyst import Analyst
from matchvoice.engine.generator import generate_match


@pytest.fixture(scope="module")
def analyst() -> Analyst:
    m = generate_match(42, "NVR", "KBY")
    a = Analyst(m.meta)
    for ev in m.events:
        a.process(ev)
    return a


def test_brief_only_holds_analyst_facts(analyst: Analyst) -> None:
    brief = build_brief(analyst, "full_time", "en", "home")
    assert brief["score"] == {"Rovers": analyst.score.home, "Kestrels": analyst.score.away}
    assert brief["favourite_team"] == "Rovers"
    assert "player_of_the_match" in brief and "since_minute" not in brief
    assert build_brief(analyst, "catch_up", "es", since=600)["since_minute"] == 10


def test_grounded_recap_is_used(analyst: Analyst, monkeypatch) -> None:
    text = f"Rovers {analyst.score.home}-{analyst.score.away} Kestrels."
    monkeypatch.setattr(pipeline, "write_recap", lambda brief, feedback=None: RecapText(paragraphs=[text]))
    res = pipeline.ai_recap(analyst, "full_time", "en")
    assert res.recap.source == "ai" and res.recap.text == text and res.attempts == 1


def test_invented_number_retries_then_falls_back_to_template(analyst: Analyst, monkeypatch) -> None:
    calls: list[str | None] = []

    def liar(brief, feedback=None):
        calls.append(feedback)
        return RecapText(paragraphs=["Rovers won with 77 shots."])

    monkeypatch.setattr(pipeline, "write_recap", liar)
    res = pipeline.ai_recap(analyst, "full_time", "en")
    assert res.recap.source == "template" and res.attempts == 2 and res.problems
    assert calls[0] is None and "77" in (calls[1] or "")


def test_model_error_falls_back_to_template(analyst: Analyst, monkeypatch) -> None:
    def boom(brief, feedback=None):
        raise RuntimeError("no network")

    monkeypatch.setattr(pipeline, "write_recap", boom)
    res = pipeline.ai_recap(analyst, "half_time", "es")
    assert res.recap.source == "template" and "no network" in res.problems[0]
