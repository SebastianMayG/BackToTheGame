"""Template recaps: half time, full time and "what did I miss?".

They are the instant fallback for the Recapper agent and only use numbers from the Analyst.
"""

from __future__ import annotations

from matchvoice.engine.analyst import Analyst
from matchvoice.models import Lang, Moment, Recap, Side

_BIG = {"goal", "red_card", "penalty_awarded", "big_chance", "great_save", "momentum_swing", "xg_vs_score"}


def _result_sentence(a: Analyst, lang: Lang, final: bool) -> str:
    h, aw = a.score.home, a.score.away
    home, away = a.meta.home.short_name, a.meta.away.short_name
    if lang == "es":
        if h == aw:
            return f"{home} y {away} {'empatan' if final else 'van empatados'} {h}-{aw}."
        win, lose = (home, away) if h > aw else (away, home)
        return f"{win} {'gana' if final else 'gana por ahora'} {max(h, aw)}-{min(h, aw)} a {lose}."
    if h == aw:
        return f"{home} and {away} {'draw' if final else 'are level at'} {h}-{aw}."
    win, lose = (home, away) if h > aw else (away, home)
    return f"{win} {'beat' if final else 'lead'} {lose} {max(h, aw)}-{min(h, aw)}."


def _numbers_sentence(a: Analyst, lang: Lang) -> str:
    s = a.snapshot()
    if lang == "es":
        return (
            f"En números: xG {s.home.xg}-{s.away.xg}, tiros {s.home.shots}-{s.away.shots}, "
            f"posesión {s.home.possession_pct}%-{s.away.possession_pct}%."
        )
    return (
        f"By the numbers: xG {s.home.xg}-{s.away.xg}, shots {s.home.shots}-{s.away.shots}, "
        f"possession {s.home.possession_pct}%-{s.away.possession_pct}%."
    )


def _key_moments(moments: list[Moment], since: float, limit: int) -> list[Moment]:
    picked = [m for m in moments if m.elapsed >= since and m.type in _BIG]
    picked.sort(key=lambda m: (-m.importance, m.elapsed))
    return sorted(picked[:limit], key=lambda m: m.elapsed)


def build_recap(
    a: Analyst,
    kind: str,
    lang: Lang,
    fav_side: Side | None = None,
    since: float = 0.0,
) -> Recap:
    snap = a.snapshot()
    pom = snap.top_players[0] if snap.top_players else None
    home, away = a.meta.home.short_name, a.meta.away.short_name
    headline = f"{home} {a.score.home}-{a.score.away} {away}"

    parts: list[str] = []
    if kind == "catch_up":
        intro = (
            f"Te pongo al día desde el {_minute(since)}:"
            if lang == "es"
            else f"Here is what you missed since {_minute(since)}:"
        )
        parts.append(intro)
        moments = _key_moments(a.moments, since, 5)
        if moments:
            parts.extend(f"{m.clock} — {m.headline.get(lang, '')}" for m in moments)
        else:
            parts.append(
                "Nada decisivo, el partido sigue abierto."
                if lang == "es"
                else "Nothing decisive, the game is still open."
            )
        parts.append(_result_sentence(a, lang, final=False))
    else:
        final = kind == "full_time"
        parts.append(_result_sentence(a, lang, final))
        moments = _key_moments(a.moments, 0.0, 3)
        if moments:
            label = "Momentos clave:" if lang == "es" else "Key moments:"
            parts.append(label + " " + " ".join(f"{m.clock} {m.headline.get(lang, '')}" for m in moments))
        parts.append(_numbers_sentence(a, lang))

    if fav_side:
        mine = snap.home if fav_side == "home" else snap.away
        team = home if fav_side == "home" else away
        parts.append(
            f"Tu equipo, {team}: {mine.shots} tiros, xG {mine.xg}, {mine.pass_accuracy}% de pases completos."
            if lang == "es"
            else f"Your team, {team}: {mine.shots} shots, {mine.xg} xG, {mine.pass_accuracy}% pass accuracy."
        )
    if pom and kind != "catch_up":
        parts.append(
            f"Jugador del partido: {pom.player.name} (nota {pom.rating})."
            if lang == "es"
            else f"Player of the match: {pom.player.name} (rating {pom.rating})."
        )
    return Recap(
        kind=kind,  # type: ignore[arg-type]
        lang=lang,
        headline=headline,
        text="\n".join(parts),
        player_of_the_match=pom.player if pom and kind != "catch_up" else None,
    )


def _minute(elapsed: float) -> str:
    return f"{int(elapsed // 60)}'"
