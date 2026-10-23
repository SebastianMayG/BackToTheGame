"""Template play-by-play narration (Spanish and English).

Every event gets an instant line, so the chat and the voice never wait for an AI model.
AI agents later replace or enrich the lines for big moments; these templates are also their fallback.

Levels: 1 = big moment (always narrated and spoken), 2 = notable, 3 = routine (only on "everything").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from matchvoice.models import CommentaryLine, Lang, MatchEvent, MatchMeta, Mode, Side

BOX_X = 105 - 16.5


@dataclass
class NarrationContext:
    meta: MatchMeta
    lang: Lang = "es"
    mode: Mode = "fan"
    fav_side: Side | None = None  # the viewer's club in this match, if any
    fav_player: str | None = None

    def team_name(self, side: Side | None) -> str:
        if side is None:
            return ""
        return (self.meta.home if side == "home" else self.meta.away).short_name


def _pick(options: list[str], seq: int) -> str:
    return options[seq % len(options)]


def _name(p: dict[str, Any] | Any | None) -> str:
    if p is None:
        return "?"
    if isinstance(p, dict):
        return str(p.get("name", "?"))
    return str(getattr(p, "name", "?"))


def _surname(p: dict[str, Any] | Any | None) -> str:
    return _name(p).split(" ")[-1]


def zone_phrase(ev: MatchEvent, lang: Lang) -> str:
    """Where the ball is, from the point of view of the team on the ball (accessible mode)."""
    if ev.location is None or ev.team is None:
        return ""
    attacks_right = (ev.team == "home") == (ev.period == 1)
    ax = ev.location.x if attacks_right else 105 - ev.location.x
    ay = ev.location.y if attacks_right else 68 - ev.location.y
    if lang == "es":
        zone = (
            "en su propio campo"
            if ax < 35
            else "en el centro del campo"
            if ax < 70
            else "en el último tercio"
            if ax < BOX_X
            else "dentro del área"
        )
        side = "por la derecha" if ay < 22 else "por la izquierda" if ay > 46 else "por el centro"
    else:
        zone = (
            "in their own half"
            if ax < 35
            else "in midfield"
            if ax < 70
            else "in the final third"
            if ax < BOX_X
            else "inside the box"
        )
        side = "on the right" if ay < 22 else "on the left" if ay > 46 else "through the middle"
    return f"{zone}, {side}"


# --------------------------------------------------------------------------- templates
# Each entry: list of variants. Placeholders are filled with str.format(**values).
T: dict[Lang, dict[str, list[str]]] = {
    "es": {
        "match_start": ["¡Bienvenidos! {home} contra {away}. Todo listo para empezar."],
        "kickoff_1": ["¡Rueda el balón! Arranca el partido entre {home} y {away}."],
        "kickoff_2": ["¡Comienza el segundo tiempo! Mueve {team}."],
        "kickoff_goal": ["Saca de centro {team}, a buscar la reacción."],
        "pass_progressive": [
            "{p} filtra un pase de {dist} metros para {r}.",
            "Gran envío de {p} hacia {r}.",
            "{p} rompe líneas y encuentra a {r}.",
        ],
        "pass_cross": [
            "Centro de {p} al área...",
            "{p} manda el centro buscando a {r}...",
            "¡Centro peligroso de {p}!",
        ],
        "pass_through": ["¡Balón al espacio de {p} para {r}!", "{p} mete el pase en profundidad para {r}."],
        "pass_long": ["{p} cambia de orientación con un pase largo para {r}.", "Pelotazo de {p} buscando a {r}."],
        "pass_routine": ["{p} toca para {r}.", "{p} la pasa a {r}.", "Combina {p} con {r}."],
        "pass_intercepted": [
            "{p} intenta el pase pero lo cortan.",
            "Pase de {p} interceptado.",
            "No llega el pase de {p}.",
        ],
        "pass_out": ["El pase de {p} se va fuera.", "{p} se pasa de fuerza y la pelota sale."],
        "carry_sprint": [
            "¡{p} arranca a toda velocidad, {speed} km/h!",
            "¡Qué carrera de {p}! Va a {speed} km/h.",
            "{p} se escapa en velocidad, {dist} metros con el balón.",
        ],
        "carry_routine": ["{p} conduce el balón.", "{p} avanza con la pelota."],
        "pressure": ["{p} presiona a {t}.", "Aprieta {p} sobre {t}."],
        "tackle_won": ["¡Gran quite de {p} a {t}!", "{p} le roba el balón a {t}.", "Entrada limpia de {p}."],
        "tackle_lost": ["{t} se libra de la entrada de {p}."],
        "interception": ["{p} intercepta.", "Corta {p} y recupera para {team}."],
        "foul": ["Falta de {p} sobre {v}.", "El árbitro pita falta de {p}."],
        "foul_penalty": [
            "¡PENAL! ¡{p} derriba a {v} dentro del área!",
            "¡Penal para {victim_team}! Falta de {p} sobre {v}.",
        ],
        "card_yellow": ["Tarjeta amarilla para {p}.", "Amonestado {p}, de {team}."],
        "card_red": [
            "¡TARJETA ROJA! {p} se va expulsado. {team} se queda con diez.",
            "¡Expulsado {p}! Golpe durísimo para {team}.",
        ],
        "corner": ["Saque de esquina para {team}.", "Córner a favor de {team}. Lo va a sacar {p}."],
        "shot_open": ["¡Dispara {p}!", "¡Remate de {p}!", "¡{p} prueba desde {dist} metros!"],
        "shot_head": ["¡Cabezazo de {p}!", "¡{p} remata de cabeza!"],
        "shot_penalty": ["{p} frente al portero desde los once metros... ¡dispara!"],
        "shot_free_kick": ["{p} ejecuta el tiro libre directo...", "¡Tiro libre de {p}!"],
        "shot_off": ["¡{p} remata y se va desviado!", "Disparo de {p}... ¡fuera!", "¡Uy! {p} la manda por encima."],
        "save": ["¡ATAJA {p}!", "¡Qué parada de {p}!", "¡{p} vuela y la saca!"],
        "block": ["¡Bloqueado! {p} se interpone.", "{p} tapa el disparo."],
        "goal": [
            "¡GOOOOL! ¡{p} marca para {team}! {home} {h}, {away} {a}.",
            "¡GOOOL de {team}! ¡{p} no perdona! {home} {h}, {away} {a}.",
        ],
        "goal_fan_for": [
            "¡¡GOOOOOOL!! ¡¡GOL DE {team_upper}!! ¡{p}, ídolo! {home} {h}, {away} {a}.",
            "¡¡SÍIII!! ¡¡GOOOL!! ¡{p} lo hace para {team}! {home} {h}, {away} {a}.",
        ],
        "goal_fan_against": [
            "Gol de {team}... marca {p}. Duro golpe. {home} {h}, {away} {a}.",
            "No puede ser... {p} anota para {team}. {home} {h}, {away} {a}.",
        ],
        "save_fan_for": ["¡¡QUÉ ATAJADA DE {p_upper}!! ¡Nuestro portero nos salva!"],
        "substitution": ["Cambio en {team}: entra {p}, sale {out}."],
        "period_end_1": ["¡Final del primer tiempo! {home} {h}, {away} {a}."],
        "period_end_2": ["¡Termina el partido! Resultado final: {home} {h}, {away} {a}."],
    },
    "en": {
        "match_start": ["Welcome! {home} against {away}. We are all set."],
        "kickoff_1": ["And we are underway! {home} versus {away}."],
        "kickoff_2": ["The second half is underway! {team} get us going."],
        "kickoff_goal": ["{team} restart, looking for a response."],
        "pass_progressive": [
            "{p} threads a {dist} metre pass to {r}.",
            "Lovely ball from {p} to {r}.",
            "{p} breaks the lines and finds {r}.",
        ],
        "pass_cross": [
            "{p} crosses into the box...",
            "{p} whips it in looking for {r}...",
            "Dangerous cross from {p}!",
        ],
        "pass_through": ["Through ball from {p} for {r}!", "{p} slides {r} in behind."],
        "pass_long": ["{p} switches play with a long ball to {r}.", "{p} goes long for {r}."],
        "pass_routine": ["{p} to {r}.", "{p} plays it to {r}.", "{p} and {r} combine."],
        "pass_intercepted": [
            "{p} tries the pass but it is cut out.",
            "{p}'s pass is intercepted.",
            "{p}'s pass doesn't find its man.",
        ],
        "pass_out": ["{p}'s pass runs out of play.", "Overhit by {p}, out it goes."],
        "carry_sprint": [
            "{p} bursts forward at {speed} km/h!",
            "What a run from {p}! {speed} km/h.",
            "{p} races away, {dist} metres with the ball.",
        ],
        "carry_routine": ["{p} carries it forward.", "{p} on the ball."],
        "pressure": ["{p} closes down {t}.", "{p} presses {t}."],
        "tackle_won": ["Great tackle from {p} on {t}!", "{p} wins it back from {t}.", "Clean challenge by {p}."],
        "tackle_lost": ["{t} rides the challenge from {p}."],
        "interception": ["{p} intercepts.", "{p} reads it and wins it back for {team}."],
        "foul": ["Foul by {p} on {v}.", "The referee blows for a foul by {p}."],
        "foul_penalty": ["PENALTY! {p} brings down {v} in the box!", "Penalty to {victim_team}! {p} fouls {v}."],
        "card_yellow": ["Yellow card for {p}.", "{p} of {team} goes into the book."],
        "card_red": ["RED CARD! {p} is sent off. {team} are down to ten.", "{p} is off! A huge blow for {team}."],
        "corner": ["Corner to {team}.", "{team} win a corner. {p} will take it."],
        "shot_open": ["{p} shoots!", "Strike from {p}!", "{p} tries his luck from {dist} metres!"],
        "shot_head": ["Header from {p}!", "{p} rises and heads it!"],
        "shot_penalty": ["{p} steps up from twelve yards... he shoots!"],
        "shot_free_kick": ["{p} lines up the free kick...", "Free kick from {p}!"],
        "shot_off": ["{p} shoots and it's wide!", "{p} strikes... just off target!", "Oh! {p} blazes it over."],
        "save": ["SAVED by {p}!", "What a stop from {p}!", "{p} flies across to keep it out!"],
        "block": ["Blocked! {p} gets in the way.", "{p} throws himself in front of it."],
        "goal": [
            "GOAL! {p} scores for {team}! {home} {h}, {away} {a}.",
            "GOAL for {team}! {p} makes no mistake! {home} {h}, {away} {a}.",
        ],
        "goal_fan_for": [
            "GOOOAL!! {team_upper} SCORE!! {p}, take a bow! {home} {h}, {away} {a}.",
            "YES!! GOAL!! {p} does it for {team}! {home} {h}, {away} {a}.",
        ],
        "goal_fan_against": [
            "{team} score... {p} with the goal. That hurts. {home} {h}, {away} {a}.",
            "Oh no... {p} puts {team} on the board. {home} {h}, {away} {a}.",
        ],
        "save_fan_for": ["WHAT A SAVE FROM {p_upper}!! Our keeper to the rescue!"],
        "substitution": ["Change for {team}: {p} comes on for {out}."],
        "period_end_1": ["Half time! {home} {h}, {away} {a}."],
        "period_end_2": ["Full time! The final score: {home} {h}, {away} {a}."],
    },
}


def _line(key: str, ctx: NarrationContext, seq: int, **values: Any) -> str:
    return _pick(T[ctx.lang][key], seq).format(**values)


def narrate_event(ev: MatchEvent, ctx: NarrationContext) -> CommentaryLine | None:
    """Instant template line for one event, or None when the event is not worth a line."""
    d = ev.data
    lang = ctx.lang
    p = _surname(ev.player)
    team = ctx.team_name(ev.team)
    home, away = ctx.meta.home.short_name, ctx.meta.away.short_name
    score = {"home": home, "away": away, "h": ev.score.home, "a": ev.score.away}
    level: int = 3
    emotion = "neutral"
    speaker = "narrator"
    key: str | None = None
    values: dict[str, Any] = {"p": p, "team": team, **score}

    t = ev.type
    if t == "match_start":
        key, level, speaker = "match_start", 1, "system"
    elif t == "kickoff":
        restart = d.get("restart", "goal")
        key = {"period_1": "kickoff_1", "period_2": "kickoff_2"}.get(restart, "kickoff_goal")
        level = 1 if key != "kickoff_goal" else 3
    elif t == "pass":
        values.update(r=_surname(d.get("recipient") or d.get("intended_recipient")), dist=round(d["distance"]))
        if d["outcome"] == "complete":
            kind = d["kind"]
            if kind == "cross":
                key, level = "pass_cross", 2
            elif kind == "through":
                key, level = "pass_through", 2
            elif d["progressive"] >= 18 and d["difficulty"] >= 0.45:
                key, level = "pass_progressive", 2
            elif kind == "long":
                key, level = "pass_long", 3
            else:
                key = "pass_routine"
        elif d["outcome"] == "intercepted":
            key = "pass_intercepted"
        else:
            key = "pass_out"
    elif t == "carry":
        values.update(speed=round(d["top_speed_kmh"], 1), dist=round(d["distance"]))
        if d["sprint"]:
            key, level = "carry_sprint", 2 if d["top_speed_kmh"] >= 31 else 3
        else:
            key = "carry_routine"
    elif t == "pressure":
        key = "pressure"
        values["t"] = _surname(d.get("target_player"))
    elif t == "tackle":
        values["t"] = _surname(d.get("target_player"))
        if d["outcome"] == "won":
            key, level = "tackle_won", 2
        elif d["outcome"] == "lost":
            key = "tackle_lost"
    elif t == "interception":
        key = "interception"
    elif t == "foul":
        values.update(v=_surname(d.get("victim")))
        if d.get("penalty"):
            victim_side: Side = "away" if ev.team == "home" else "home"
            values["victim_team"] = ctx.team_name(victim_side)
            key, level, emotion = "foul_penalty", 1, "excited"
        else:
            key, level = "foul", 3
    elif t == "card":
        if d["color"] == "red":
            key, level, emotion = "card_red", 1, "tense"
        else:
            key, level = "card_yellow", 2
    elif t == "corner":
        key, level = "corner", 2
    elif t == "shot":
        values["dist"] = round(d["distance_to_goal"])
        sit = d["situation"]
        if d["outcome"] == "off_target":
            key = "shot_off"
        elif sit == "penalty":
            key = "shot_penalty"
        elif sit == "free_kick":
            key = "shot_free_kick"
        elif d["body_part"] == "head":
            key = "shot_head"
        else:
            key = "shot_open"
        big = d["xg"] >= 0.25 or d["outcome"] in ("goal", "saved")
        level = 1 if big else 2
        emotion = "excited" if big else "tense"
    elif t == "save":
        key, level, emotion = "save", 1, "excited"
        if ctx.fav_side and ev.team == ctx.fav_side:
            key = "save_fan_for"
            values["p_upper"] = p.upper()
    elif t == "block":
        key, level = "block", 2
    elif t == "goal":
        level, emotion = 1, "excited"
        values["team_upper"] = team.upper()
        if ctx.fav_side and ctx.mode == "fan":
            if ev.team == ctx.fav_side:
                key = "goal_fan_for"
            else:
                key, emotion = "goal_fan_against", "disappointed"
        else:
            key = "goal"
    elif t == "substitution":
        key, level = "substitution", 2
        values["out"] = _surname(d.get("player_out"))
    elif t == "period_end":
        key, level, speaker = f"period_end_{d['period']}", 1, "system"

    if key is None:
        return None

    text = _line(key, ctx, ev.seq, **values)
    if ctx.mode == "accessible" and t in ("pass", "carry", "shot", "tackle", "interception"):
        where = zone_phrase(ev, lang)
        if where:
            text = f"{text[:-1] if text.endswith('.') else text} — {where}."
            level = min(level, 2)  # accessible mode describes the build-up too
    if ctx.fav_player and ev.player and ev.player.id == ctx.fav_player:
        text = f"⭐ {text}"
        if t in ("shot", "tackle", "interception", "carry") and level == 3:
            level = 2  # the viewer's player gets their notable actions narrated

    return CommentaryLine(
        id=f"pbp-{ev.seq}-{lang}",
        event_id=ev.id,
        elapsed=ev.elapsed,
        clock=ev.clock.display,
        speaker=speaker,  # type: ignore[arg-type]
        level=level,  # type: ignore[arg-type]
        lang=lang,
        text=text,
        emotion=emotion,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------- moment headlines
MOMENT_T: dict[Lang, dict[str, str]] = {
    "es": {
        "goal": "{scorer} marca para {team} ({context}). xG del remate: {xg}.",
        "big_chance": "¡Ocasión clarísima para {team}! {shooter} falla una de {xg_pct}% de probabilidad.",
        "great_save": "Paradón de {keeper} ante {shooter}: un disparo de {speed} km/h y {xg_pct}% de gol.",
        "momentum_swing": "{team} toma el control: domina la amenaza de los últimos 5 minutos ({threat_share_pct}%).",
        "rhythm_shift_chaos": "Partido de ida y vuelta: {changes} cambios de posesión en 5 minutos. Caos total.",
        "rhythm_shift_control": "{team} pone pausa: controla el ritmo con {possession}% de posesión reciente.",
        "pressing_spell": "{team} presiona arriba: {regains} recuperaciones en campo rival en 5 minutos.",
        "xg_vs_score": "{team} merece más: {xg_for} de xG contra {xg_against}, pero no va ganando.",
        "penalty_awarded": "¡Penal para {team}! {victim} cae dentro del área.",
        "red_card": "¡Roja para {player}! {team} jugará con diez.",
        "yellow_card": "Amarilla para {player} ({team}).",
        "substitution": "Cambio en {team}: entra {player_in} por {player_out}.",
        "speed_alert": "⚡ {player} alcanza {speed} km/h.",
        "rocket_shot": "🚀 ¡Misil de {player}! El disparo sale a {speed} km/h.",
        "quality_pass": "🎯 Pase de calidad de {player}: {distance} m, dificultad {difficulty}.",
        "half_time": "Descanso: {home} {h}-{a} {away}. xG {xg_home}-{xg_away}.",
        "full_time": "Final: {home} {h}-{a} {away}. xG {xg_home}-{xg_away}.",
    },
    "en": {
        "goal": "{scorer} scores for {team} ({context}). Shot xG: {xg}.",
        "big_chance": "Huge chance for {team}! {shooter} misses a {xg_pct}% opportunity.",
        "great_save": "Big save from {keeper} to deny {shooter}: {speed} km/h, a {xg_pct}% chance.",
        "momentum_swing": "{team} take control: {threat_share_pct}% of the threat in the last 5 minutes.",
        "rhythm_shift_chaos": "End to end: {changes} changes of possession in 5 minutes. Pure chaos.",
        "rhythm_shift_control": "{team} slow it down and control the tempo with {possession}% recent possession.",
        "pressing_spell": "{team} press high: {regains} ball recoveries in the opposition half in 5 minutes.",
        "xg_vs_score": "{team} deserve more: {xg_for} xG against {xg_against}, yet they are not winning.",
        "penalty_awarded": "Penalty to {team}! {victim} goes down in the box.",
        "red_card": "Red card for {player}! {team} down to ten.",
        "yellow_card": "Yellow card for {player} ({team}).",
        "substitution": "{team} change: {player_in} on for {player_out}.",
        "speed_alert": "⚡ {player} hits {speed} km/h.",
        "rocket_shot": "🚀 Rocket from {player}! That shot left the boot at {speed} km/h.",
        "quality_pass": "🎯 Quality pass from {player}: {distance} m, difficulty {difficulty}.",
        "half_time": "Half time: {home} {h}-{a} {away}. xG {xg_home}-{xg_away}.",
        "full_time": "Full time: {home} {h}-{a} {away}. xG {xg_home}-{xg_away}.",
    },
}

GOAL_CONTEXT: dict[Lang, dict[str, str]] = {
    "es": {
        "opener": "abre el marcador",
        "equaliser": "empata el partido",
        "go_ahead": "pone por delante a su equipo",
        "extends_lead": "amplía la ventaja",
        "consolation": "descuenta",
        "brace": "doblete",
        "hat_trick": "¡triplete!",
        "against_run": "contra la corriente del juego",
    },
    "en": {
        "opener": "opens the scoring",
        "equaliser": "levels it",
        "go_ahead": "puts them ahead",
        "extends_lead": "extends the lead",
        "consolation": "pulls one back",
        "brace": "a brace",
        "hat_trick": "a hat-trick!",
        "against_run": "against the run of play",
    },
}


def moment_headline(moment_type: str, facts: dict[str, Any], lang: Lang) -> str:
    key = moment_type
    if moment_type == "rhythm_shift":
        key = f"rhythm_shift_{facts.get('rhythm', 'chaos')}"
    template = MOMENT_T[lang].get(key)
    if not template:
        return ""
    values = dict(facts)
    if moment_type == "goal":
        values["context"] = ", ".join(GOAL_CONTEXT[lang][c] for c in facts.get("context", []))
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        return template
