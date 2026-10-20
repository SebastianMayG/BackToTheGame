import json

from fastapi.testclient import TestClient

from matchvoice.main import app

client = TestClient(app)


def test_health_and_clubs():
    assert client.get("/api/health").json()["status"] == "ok"
    clubs = client.get("/api/clubs").json()["clubs"]
    assert len(clubs) == 4 and all(len(c["squad"]) == 16 for c in clubs)


def test_match_and_analysis():
    m = client.get("/api/matches/42").json()
    assert m["meta"]["match_id"] == "NVR-KBY-42"
    a = client.get("/api/matches/42/analysis").json()
    assert a["moments"] and a["stats"]["home"]["shots"] >= 0


def test_bad_club_is_400():
    assert client.get("/api/matches/1?home=XXX").status_code == 400


def test_catchup_and_export():
    r = client.get("/api/matches/42/catchup", params={"until": 3600, "since": 1800, "lang": "en"}).json()
    assert r["kind"] == "catch_up" and r["text"]
    csv = client.get("/api/matches/42/export?format=csv")
    assert csv.status_code == 200 and csv.text.startswith("seq,clock")


def test_stream_emits_events_lines_and_stats():
    seen: dict[str, int] = {}
    with client.stream("GET", "/api/matches/42/stream", params={"speed": 240, "lang": "es"}) as r:
        event = None
        for raw in r.iter_lines():
            if raw.startswith("event:"):
                event = raw.split(":", 1)[1].strip()
                seen[event] = seen.get(event, 0) + 1
            elif raw.startswith("data:") and event == "pbp":
                assert json.loads(raw[5:])["lang"] == "es"
            if seen.get("match_event", 0) >= 60:
                break
    assert seen.get("meta") == 1
    assert seen.get("pbp", 0) > 10
    assert seen.get("stats", 0) >= 1
