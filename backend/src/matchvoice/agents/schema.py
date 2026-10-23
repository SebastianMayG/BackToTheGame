from typing import Literal

from pydantic import BaseModel


class Explanation(BaseModel):
    why: str
    tactical_angle: str
    key_numbers: list[str]
    confidence: float


class Line(BaseModel):
    speaker: Literal["narrator", "pundit"]
    lang: Literal["es", "en"]
    text: str
    emotion: Literal["neutral", "excited", "tense", "disappointed"]


class Commentary(BaseModel):
    lines: list[Line]


class RecapText(BaseModel):
    paragraphs: list[str]


class Answer(BaseModel):
    answer: str
    event_ids: list[str]


class QueryPlan(BaseModel):
    """The Analyst Query agent's reading of a request. Code turns it into an OverlaySpec."""

    understood: bool
    layer: Literal["shot_map", "heatmap", "progressive_passes"] | None
    team: Literal["home", "away"] | None
    player_id: str | None
    period: Literal[1, 2] | None
    from_minute: float | None
    to_minute: float | None
