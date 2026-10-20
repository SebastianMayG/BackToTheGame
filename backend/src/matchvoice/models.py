"""Data contracts shared by the engine, the API and (through OpenAPI) the Vue frontend."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Side = Literal["home", "away"]
Lang = Literal["es", "en"]
Mode = Literal["fan", "analyst", "accessible"]

EventType = Literal[
    "match_start",
    "period_start",
    "kickoff",
    "pass",
    "carry",
    "pressure",
    "tackle",
    "interception",
    "possession_change",
    "foul",
    "card",
    "corner",
    "shot",
    "save",
    "block",
    "goal",
    "substitution",
    "period_end",
    "match_end",
]

MomentType = Literal[
    "goal",
    "big_chance",
    "great_save",
    "momentum_swing",
    "rhythm_shift",
    "pressing_spell",
    "xg_vs_score",
    "penalty_awarded",
    "red_card",
    "yellow_card",
    "substitution",
    "speed_alert",
    "rocket_shot",
    "quality_pass",
    "half_time",
    "full_time",
]


class Style(BaseModel):
    """How a club plays. Every value is 0..1."""

    press: float
    directness: float
    quality: float
    width: float


class Player(BaseModel):
    id: str
    name: str
    number: int
    position: str  # role code: GK, RB, RCB, LCB, LB, DM, RCM, LCM, RW, ST, LW (bench: SUB_*)
    quality: float = Field(ge=0, le=1)
    top_speed_kmh: float


class PlayerRef(BaseModel):
    """Compact player reference used inside events."""

    id: str
    name: str
    number: int
    position: str


class Club(BaseModel):
    id: str
    name: str
    short_name: str
    primary_color: str
    secondary_color: str
    style: Style
    squad: list[Player]


class Location(BaseModel):
    """Absolute pitch coordinates in metres: x 0..105, y 0..68."""

    x: float
    y: float


class Clock(BaseModel):
    minute: int
    second: int
    stoppage: int = 0  # seconds into stoppage time
    display: str


class Score(BaseModel):
    home: int = 0
    away: int = 0


class Possession(BaseModel):
    id: int
    team: Side | None


class MatchEvent(BaseModel):
    id: str
    seq: int
    match_id: str
    type: EventType
    period: Literal[1, 2]
    elapsed: float  # seconds of play since kickoff (half-time break excluded); drives replay timing
    clock: Clock
    team: Side | None = None
    player: PlayerRef | None = None
    location: Location | None = None
    possession: Possession
    score: Score
    data: dict[str, Any] = Field(default_factory=dict)


class MatchMeta(BaseModel):
    match_id: str
    seed: int
    home: Club
    away: Club
    stoppage_minutes: dict[str, int]  # {"1": 2, "2": 4}
    pitch: dict[str, float] = Field(default_factory=lambda: {"length": 105.0, "width": 68.0})


class Match(BaseModel):
    meta: MatchMeta
    events: list[MatchEvent]


class Moment(BaseModel):
    """A key moment detected by the Analyst engine. The evidence is what AI agents will build on."""

    id: str
    type: MomentType
    importance: float = Field(ge=0, le=1)
    elapsed: float
    clock: str
    team: Side | None = None
    players: list[PlayerRef] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    event_ids: list[str] = Field(default_factory=list)
    headline: dict[str, str] = Field(default_factory=dict)  # template headline per language


class TeamStats(BaseModel):
    goals: int = 0
    possession_pct: float = 50.0
    passes: int = 0
    passes_completed: int = 0
    pass_accuracy: float = 0.0
    progressive_passes: int = 0
    final_third_passes: int = 0
    box_entries: int = 0
    shots: int = 0
    shots_on_target: int = 0
    xg: float = 0.0
    corners: int = 0
    fouls: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    tackles_won: int = 0
    interceptions: int = 0
    pressures: int = 0
    saves: int = 0
    ppda: float | None = None
    field_tilt_pct: float = 50.0
    top_shot_speed_kmh: float = 0.0


class PlayerStats(BaseModel):
    player: PlayerRef
    team: Side
    passes: int = 0
    passes_completed: int = 0
    progressive_passes: int = 0
    key_passes: int = 0
    shots: int = 0
    shots_on_target: int = 0
    xg: float = 0.0
    goals: int = 0
    assists: int = 0
    tackles_won: int = 0
    interceptions: int = 0
    pressures: int = 0
    saves: int = 0
    sprints: int = 0
    top_speed_kmh: float = 0.0
    carry_distance_m: float = 0.0
    yellow_cards: int = 0
    red_cards: int = 0
    rating: float = 6.0


class StatsSnapshot(BaseModel):
    elapsed: float
    clock: str
    score: Score
    home: TeamStats
    away: TeamStats
    momentum: float  # -1 (away on top) .. +1 (home on top), last 5 minutes
    rhythm: Literal["control", "balanced", "chaos"]
    top_players: list[PlayerStats]


class CommentaryLine(BaseModel):
    """One line in the narration chat. `source` tells the UI whether it came from a template or an AI agent."""

    id: str
    event_id: str | None = None
    moment_id: str | None = None
    elapsed: float
    clock: str
    speaker: Literal["narrator", "pundit", "system"]
    level: Literal[1, 2, 3]  # 1 = big moment, 2 = notable, 3 = routine
    lang: Lang
    text: str
    emotion: Literal["neutral", "excited", "tense", "disappointed"] = "neutral"
    source: Literal["template", "ai"] = "template"


class Recap(BaseModel):
    kind: Literal["half_time", "full_time", "catch_up"]
    lang: Lang
    headline: str
    text: str
    player_of_the_match: PlayerRef | None = None
    source: Literal["template", "ai"] = "template"


class Profile(BaseModel):
    """Viewer personalisation. Sent as query parameters on the stream."""

    lang: Lang = "es"
    mode: Mode = "fan"
    club: str | None = None  # club id
    player: str | None = None  # player id
