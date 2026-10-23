from __future__ import annotations

from fastapi.testclient import TestClient

from matchvoice.api import voice as voice_api
from matchvoice.main import app
from matchvoice.voice.speech import SpeechUnavailable, build_ssml

client = TestClient(app)
BODY = {"text": "What a save!", "speaker": "narrator", "lang": "en", "emotion": "excited"}


def test_ssml_uses_a_different_voice_per_actor() -> None:
    narrator = build_ssml("Gol", "narrator", "es", "excited")
    pundit = build_ssml("Gol", "pundit", "es", "neutral")
    assert "es-MX-JorgeNeural" in narrator and "es-MX-DaliaNeural" in pundit
    assert "xmlns='http://www.w3.org/2001/10/synthesis'" in narrator
    assert "rate='+12%'" in narrator


def test_ssml_escapes_the_text() -> None:
    ssml = build_ssml("Tom & <Jerry>", "narrator", "en", "neutral")
    assert "Tom &amp; &lt;Jerry&gt;" in ssml


def test_voice_is_503_when_speech_is_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(voice_api, "is_configured", lambda: False)
    assert client.post("/api/voice", json=BODY).status_code == 503


def test_voice_returns_audio(monkeypatch) -> None:
    monkeypatch.setattr(voice_api, "is_configured", lambda: True)
    monkeypatch.setattr(voice_api, "synthesize", lambda *a: b"mp3")
    res = client.post("/api/voice", json=BODY)
    assert res.status_code == 200 and res.headers["content-type"] == "audio/mpeg" and res.content == b"mp3"


def test_voice_is_502_when_azure_fails(monkeypatch) -> None:
    def boom(*a):
        raise SpeechUnavailable("denied")

    monkeypatch.setattr(voice_api, "is_configured", lambda: True)
    monkeypatch.setattr(voice_api, "synthesize", boom)
    assert client.post("/api/voice", json=BODY).status_code == 502
