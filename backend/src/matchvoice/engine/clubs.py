"""Four fictional clubs with their own playing style and fixed squads.

Squads are generated from each club id (not from the match seed), so a fan's favourite player
is the same in every match.
"""

from __future__ import annotations

import random
import zlib
from functools import cache

from matchvoice.models import Club, Player, Style

# Starting XI in a 4-3-3, then the bench.
STARTING_ROLES = ["GK", "RB", "RCB", "LCB", "LB", "DM", "RCM", "LCM", "RW", "ST", "LW"]
BENCH_ROLES = ["SUB_GK", "SUB_DEF", "SUB_MID", "SUB_WING", "SUB_ST"]
SHIRT_NUMBERS = {
    "GK": 1,
    "RB": 2,
    "RCB": 4,
    "LCB": 5,
    "LB": 3,
    "DM": 6,
    "RCM": 8,
    "LCM": 10,
    "RW": 7,
    "ST": 9,
    "LW": 11,
    "SUB_GK": 13,
    "SUB_DEF": 15,
    "SUB_MID": 16,
    "SUB_WING": 17,
    "SUB_ST": 19,
}

FIRST_NAMES = [
    "Mateo",
    "Kofi",
    "Luca",
    "Hiro",
    "Ezra",
    "Tomás",
    "Idris",
    "Sven",
    "Rafael",
    "Nico",
    "Amadou",
    "Jonas",
    "Kai",
    "Diego",
    "Malik",
    "Teodor",
    "Rui",
    "Emeka",
    "Felix",
    "Joaquín",
    "Oskar",
    "Yuto",
    "Bastien",
    "Samir",
    "Leon",
    "Andrés",
    "Callum",
    "Dario",
    "Ilan",
    "Marek",
    "Thiago",
    "Kwame",
    "Elias",
    "Bruno",
    "Aurelio",
    "Finn",
    "Lamar",
    "Pavel",
    "Iker",
    "Soren",
]
LAST_NAMES = [
    "Okafor",
    "Varela",
    "Lindqvist",
    "Moreau",
    "Tanaka",
    "Ruiz",
    "Mendes",
    "Haddad",
    "Novak",
    "Brennan",
    "Asante",
    "Kowalski",
    "Ferreira",
    "Dahl",
    "Castell",
    "Obi",
    "Marchetti",
    "Sato",
    "Quiroga",
    "Eriksen",
    "Delacroix",
    "Abara",
    "Kessler",
    "Rossi",
    "Mbeki",
    "Salas",
    "Vukovic",
    "Ortega",
    "Fontaine",
    "Achterberg",
    "Nakamura",
    "Ibarra",
    "Kruger",
    "Lennox",
    "Vidal",
    "Petrov",
    "Duarte",
    "Wexler",
    "Arroyo",
    "Sandoval",
]

# Rough top speed and quality bands by role.
_ROLE_SPEED = {"GK": (27, 30), "CB": (30, 33), "FB": (32, 35), "MID": (30, 33.5), "WING": (33, 36), "ST": (32, 35)}


def role_group(role: str) -> str:
    r = role.removeprefix("SUB_")
    if r == "GK":
        return "GK"
    if r in ("RCB", "LCB", "DEF"):
        return "CB"
    if r in ("RB", "LB"):
        return "FB"
    if r in ("DM", "RCM", "LCM", "MID"):
        return "MID"
    if r in ("RW", "LW", "WING"):
        return "WING"
    return "ST"


_CLUB_DEFS = [
    (
        "NVR",
        "Northvale Rovers",
        "Rovers",
        "#c8102e",
        "#ffffff",
        Style(press=0.75, directness=0.35, quality=0.80, width=0.6),
    ),
    (
        "KBY",
        "Kestrel Bay",
        "Kestrels",
        "#1d4ed8",
        "#facc15",
        Style(press=0.45, directness=0.65, quality=0.72, width=0.75),
    ),
    (
        "SLA",
        "Silverlake Athletic",
        "Silverlake",
        "#0f766e",
        "#e5e7eb",
        Style(press=0.60, directness=0.45, quality=0.76, width=0.5),
    ),
    (
        "CRC",
        "Corran City",
        "Corran",
        "#7c3aed",
        "#f97316",
        Style(press=0.55, directness=0.55, quality=0.74, width=0.65),
    ),
]


def _make_squad(club_id: str, base_quality: float) -> list[Player]:
    rng = random.Random(zlib.crc32(club_id.encode()))
    used: set[str] = set()
    players: list[Player] = []
    for role in STARTING_ROLES + BENCH_ROLES:
        while True:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            if name not in used:
                used.add(name)
                break
        lo, hi = _ROLE_SPEED[role_group(role)]
        bench_penalty = 0.04 if role.startswith("SUB_") else 0.0
        quality = max(0.5, min(0.95, rng.gauss(base_quality - bench_penalty, 0.05)))
        players.append(
            Player(
                id=f"{club_id}-{SHIRT_NUMBERS[role]}",
                name=name,
                number=SHIRT_NUMBERS[role],
                position=role,
                quality=round(quality, 3),
                top_speed_kmh=round(rng.uniform(lo, hi), 1),
            )
        )
    return players


@cache
def all_clubs() -> dict[str, Club]:
    return {
        cid: Club(
            id=cid,
            name=name,
            short_name=short,
            primary_color=primary,
            secondary_color=secondary,
            style=style,
            squad=_make_squad(cid, style.quality),
        )
        for cid, name, short, primary, secondary, style in _CLUB_DEFS
    }


def get_club(club_id: str) -> Club:
    clubs = all_clubs()
    if club_id not in clubs:
        raise KeyError(f"Unknown club {club_id!r}. Known: {', '.join(clubs)}")
    return clubs[club_id]
