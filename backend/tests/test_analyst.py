from matchvoice.engine.analyst import Analyst
from matchvoice.engine.generator import generate_match
from matchvoice.engine.recap import build_recap


def run(seed: int = 42):
    m = generate_match(seed)
    a = Analyst(m.meta)
    for ev in m.events:
        a.process(ev)
    return m, a


def test_stats_match_raw_events():
    m, a = run()
    s = a.snapshot()
    for side, ts in (("home", s.home), ("away", s.away)):
        ev = [e for e in m.events if e.team == side]
        assert ts.shots == sum(e.type == "shot" for e in ev)
        assert ts.passes == sum(e.type == "pass" for e in ev)
        assert ts.goals == sum(e.type == "goal" for e in ev)
        assert abs(ts.xg - sum(e.data["xg"] for e in ev if e.type == "shot")) < 0.02
    assert abs(s.home.possession_pct + s.away.possession_pct - 100) < 0.5
    assert -1 <= s.momentum <= 1


def test_every_goal_is_a_moment_with_evidence():
    m, a = run(5)
    goals = [e for e in m.events if e.type == "goal"]
    goal_moments = [mo for mo in a.moments if mo.type == "goal"]
    assert len(goal_moments) == len(goals)
    for mo, ev in zip(goal_moments, goals, strict=True):
        assert ev.id in mo.event_ids
        assert mo.importance == 1.0
        assert mo.headline["es"] and mo.headline["en"]
        assert mo.facts["context"]


def test_half_and_full_time_moments():
    _, a = run(9)
    types = [mo.type for mo in a.moments]
    assert types.count("half_time") == 1
    assert types[-1] == "full_time"


def test_moments_cover_several_types_across_matches():
    seen = set()
    for seed in range(8):
        _, a = run(seed)
        seen |= {mo.type for mo in a.moments}
    for expected in ("goal", "great_save", "momentum_swing", "speed_alert", "substitution", "yellow_card"):
        assert expected in seen, expected


def test_player_ratings_and_assists():
    m, a = run(13)
    players = a.player_stats()
    assert all(3 <= p.rating <= 10 for p in players)
    assert sum(p.goals for p in players) == sum(e.type == "goal" for e in m.events)


def test_recaps_in_both_languages():
    _, a = run(21)
    for lang in ("es", "en"):
        full = build_recap(a, "full_time", lang, "home")
        assert full.headline and full.text and full.player_of_the_match
        catch = build_recap(a, "catch_up", lang, None, since=60 * 60)
        assert catch.text
