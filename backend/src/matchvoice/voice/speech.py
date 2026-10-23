"""Azure AI Speech text-to-speech with one voice per commentator and the emotion as prosody.

Authentication is Microsoft Entra ID (the same `DefaultAzureCredential` as the agents), so there is no
key to leak. The signed-in identity needs the "Cognitive Services Speech User" role on the Speech resource.
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from collections import OrderedDict
from xml.sax.saxutils import escape

import httpx
from azure.identity import DefaultAzureCredential

from matchvoice.agents.client import load_env

SCOPE = "https://cognitiveservices.azure.com/.default"
OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
CACHE_SIZE = 200
TIMEOUT = 15.0

# One voice per actor and language: the narrator is the energetic one, the pundit the calm one.
VOICES: dict[tuple[str, str], tuple[str, str]] = {
    ("narrator", "es"): ("es-MX-JorgeNeural", "es-MX"),
    ("pundit", "es"): ("es-MX-DaliaNeural", "es-MX"),
    ("narrator", "en"): ("en-GB-RyanNeural", "en-GB"),
    ("pundit", "en"): ("en-GB-SoniaNeural", "en-GB"),
}

# emotion -> (rate, pitch). Prosody works on every voice; express-as styles do not.
PROSODY: dict[str, tuple[str, str]] = {
    "neutral": ("0%", "0%"),
    "excited": ("+12%", "+8%"),
    "tense": ("-4%", "-4%"),
    "disappointed": ("-10%", "-10%"),
}


class SpeechUnavailable(RuntimeError):
    """Speech is not configured, or Azure refused the request."""


def is_configured() -> bool:
    load_env()
    return bool(os.environ.get("SPEECH_REGION") and os.environ.get("SPEECH_RESOURCE_ID"))


def build_ssml(text: str, speaker: str, lang: str, emotion: str) -> str:
    voice, locale = VOICES.get((speaker, lang)) or VOICES[("narrator", "en" if lang != "es" else "es")]
    rate, pitch = PROSODY.get(emotion, PROSODY["neutral"])
    if speaker == "pundit":  # the pundit stays a touch slower than the narrator
        rate = "-5%" if rate == "0%" else rate
    return (
        f"<speak version='1.0' xml:lang='{locale}' xmlns='http://www.w3.org/2001/10/synthesis'>"
        f"<voice name='{voice}'><prosody rate='{rate}' pitch='{pitch}'>{escape(text)}</prosody></voice>"
        "</speak>"
    )


class _Token:
    """Caches the Entra token until shortly before it expires."""

    def __init__(self) -> None:
        self._cred: DefaultAzureCredential | None = None
        self._value = ""
        self._expires = 0.0
        self._lock = threading.Lock()

    def get(self) -> str:
        with self._lock:
            if time.time() > self._expires - 120:
                if self._cred is None:
                    self._cred = DefaultAzureCredential()
                tok = self._cred.get_token(SCOPE)
                self._value, self._expires = tok.token, float(tok.expires_on)
            return self._value


_token = _Token()
_cache: OrderedDict[str, bytes] = OrderedDict()
_cache_lock = threading.Lock()


def _key(text: str, speaker: str, lang: str, emotion: str) -> str:
    return hashlib.sha1(f"{speaker}|{lang}|{emotion}|{text}".encode()).hexdigest()


def synthesize(text: str, speaker: str, lang: str, emotion: str = "neutral") -> bytes:
    """Return MP3 bytes. Repeated lines (replays, reconnects) come from a small in-memory cache."""
    if not is_configured():
        raise SpeechUnavailable("Speech is not configured (SPEECH_REGION, SPEECH_RESOURCE_ID)")
    key = _key(text, speaker, lang, emotion)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    region, resource_id = os.environ["SPEECH_REGION"], os.environ["SPEECH_RESOURCE_ID"]
    try:
        auth = f"Bearer aad#{resource_id}#{_token.get()}"
        res = httpx.post(
            f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
            content=build_ssml(text, speaker, lang, emotion).encode("utf-8"),
            headers={
                "Authorization": auth,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": OUTPUT_FORMAT,
                "User-Agent": "matchvoice",
            },
            timeout=TIMEOUT,
        )
    except Exception as exc:  # network or credential problems
        raise SpeechUnavailable(f"Speech request failed: {exc}") from exc
    if res.status_code != 200:
        raise SpeechUnavailable(f"Speech returned {res.status_code}: {res.text[:200]}")
    with _cache_lock:
        _cache[key] = res.content
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return res.content
