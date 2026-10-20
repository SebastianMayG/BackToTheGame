import statistics

import pytest

from matchvoice.engine.clubs import all_clubs
from matchvoice.engine.generator import expected_goals, generate_match


def test_same_seed_same_match():
    a = generate_match(7, "NVR", "KBY")
    b = generate_match(7, "NVR", "KBY")
    assert a.model_dump() == b.model_dump()


def test_different_seed_different_match():
    assert generate_match(1).events != generate_match(2).events


def test_events_are_ordered_and_well_formed():
    m = generate_match(42)
    seqs = [e.seq for e in m.events]
    assert seqs == list(range(1, len(seqs) + 1))
    assert all(b.elapsed >= a.elapsed for a, b in zip(m.events, m.events[1:], strict=False))
    assert m.events[0].type == "match_start"
    assert m.events[-1].type == "match_end"
    for e in m.events:
        if e.location:
            assert 0 <= e.location.x <= 105 and 0 <= e.location.y <= 68, e
        if e.type == "pass":
            end = e.data["end_location"]
            assert 0 <= end["x"] <= 105 and 0 <= end["y"] <= 68
            assert 0 <= e.data["difficulty"] <= 1


def test_score_matches_goal_events():
    m = generate_match(3)
    goals = [e for e in m.events if e.type == "goal"]
    final = m.events[-1].data["final_score"]
    assert sum(g.team == "home" for g in goals) == final["home"]
    assert sum(g.team == "away" for g in goals) == final["away"]


def test_squads_are_stable_and_unique():
    for club in all_clubs().values():
        assert len(club.squad) == 16
        assert len({p.id for p in club.squad}) == 16
        assert len({p.name for p in club.squad}) == 16


def test_substitutions_and_lineups():
    m = generate_match(11)
    subs = [e for e in m.events if e.type == "substitution"]
    assert 1 <= sum(e.team == "home" for e in subs) <= 3
    assert all(e.period == 2 for e in subs)


def test_xg_model_is_sensible():
    assert expected_goals(94, 34) > expected_goals(80, 34)  # closer is better
    assert expected_goals(94, 34) > expected_goals(94, 5)  # central is better than a tight angle
    assert expected_goals(94, 34, "head") < expected_goals(94, 34, "foot")


def test_unknown_club():
    with pytest.raises(KeyError):
        generate_match(1, "XXX", "KBY")


@pytest.mark.parametrize(
    ("metric", "lo", "hi"),
    [("goals", 0.9, 2.2), ("shots", 9, 18), ("passes", 380, 620), ("acc", 0.74, 0.88), ("fouls", 8, 16)],
)
def test_realism_over_many_matches(metric, lo, hi):
    values = []
    for seed in range(25):
        m = generate_match(seed)
        for side in ("home", "away"):
            ev = [e for e in m.events if e.team == side]
            passes = [e for e in ev if e.type == "pass"]
            values.append(
                {
                    "goals": sum(e.type == "goal" for e in ev),
                    "shots": sum(e.type == "shot" for e in ev),
                    "passes": len(passes),
                    "acc": sum(e.data["outcome"] == "complete" for e in passes) / len(passes),
                    "fouls": sum(e.type == "foul" for e in ev),
                }[metric]
            )
    assert lo <= statistics.mean(values) <= hi
