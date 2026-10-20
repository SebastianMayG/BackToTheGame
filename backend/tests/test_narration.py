from matchvoice.engine.generator import generate_match
from matchvoice.engine.narration import NarrationContext, narrate_event


def lines(seed=42, **ctx):
    m = generate_match(seed)
    c = NarrationContext(meta=m.meta, **ctx)
    return m, [(ev, narrate_event(ev, c)) for ev in m.events]


def test_every_big_event_gets_a_line_in_both_languages():
    for lang in ("es", "en"):
        _, out = lines(lang=lang)
        for ev, line in out:
            if ev.type in ("goal", "shot", "save", "card", "corner", "substitution", "period_end"):
                assert line is not None, ev.type
                assert line.lang == lang
                assert "{" not in line.text, line.text  # every placeholder filled


def test_goals_are_level_one_and_excited():
    _, out = lines(5)
    goal_lines = [line for ev, line in out if ev.type == "goal"]
    assert goal_lines
    assert all(line.level == 1 and line.emotion == "excited" for line in goal_lines)


def test_fan_perspective_changes_goal_lines():
    m, neutral = lines(5)
    _, fan_home = lines(5, fav_side="home")
    goals = [i for i, (ev, _) in enumerate(neutral) if ev.type == "goal"]
    assert any(neutral[i][1].text != fan_home[i][1].text for i in goals)
    conceded = [i for i in goals if neutral[i][0].team == "away"]
    for i in conceded:
        assert fan_home[i][1].emotion == "disappointed"


def test_accessible_mode_describes_location():
    _, out = lines(mode="accessible", lang="es")
    passes = [line for ev, line in out if ev.type == "pass" and line]
    assert any("campo" in line.text or "área" in line.text for line in passes)


def test_favourite_player_lines_are_marked():
    m, _ = lines()
    fav = m.meta.home.squad[9].id  # the starting striker
    _, out = lines(fav_player=fav)
    marked = [line for ev, line in out if line and ev.player and ev.player.id == fav and line.text.startswith("⭐")]
    assert marked
