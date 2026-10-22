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
