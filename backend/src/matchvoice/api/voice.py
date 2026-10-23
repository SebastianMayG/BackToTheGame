"""POST /api/voice: one commentary line in, MP3 out."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from matchvoice.voice.speech import SpeechUnavailable, is_configured, synthesize

router = APIRouter(prefix="/api", tags=["voice"])


class VoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=400)
    speaker: Literal["narrator", "pundit"] = "narrator"
    lang: Literal["es", "en"] = "en"
    emotion: Literal["neutral", "excited", "tense", "disappointed"] = "neutral"


@router.get("/voice/status")
def voice_status() -> dict[str, bool]:
    return {"configured": is_configured()}


@router.post("/voice", response_class=Response, responses={200: {"content": {"audio/mpeg": {}}}})
async def voice(req: VoiceRequest) -> Response:
    """Neural text-to-speech. The status code tells the UI when to fall back to the browser voice."""
    if not is_configured():
        raise HTTPException(503, "Speech is not configured")
    try:
        audio = await asyncio.to_thread(synthesize, req.text, req.speaker, req.lang, req.emotion)
    except SpeechUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=3600"})
