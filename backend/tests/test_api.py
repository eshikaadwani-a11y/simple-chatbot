"""FastAPI endpoint tests using TestClient (no LLM/DB required)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_meta_models_lists_default_and_available():
    res = client.get("/meta/models")
    assert res.status_code == 200
    body = res.json()
    assert body["default"]
    assert "gpt-5" in body["available"]


def test_auth_me_dev_mode():
    res = client.get("/auth/me")
    assert res.status_code == 200
    assert res.json()["user_id"] == "dev-user"


def test_progress_event_and_summary_roundtrip():
    # Record a completed topic, then read the dashboard summary.
    res = client.post(
        "/progress/event",
        json={"type": "topic_completed", "topic": "Recursion", "mastery": 0.9},
    )
    assert res.status_code == 200 and res.json()["ok"] is True

    summary = client.get("/progress/summary").json()
    assert summary["topics_completed"] == 1
    assert summary["xp"] >= 25


def test_progress_event_rejects_incomplete_payload():
    res = client.post("/progress/event", json={"type": "quiz_result"})  # missing topic
    assert res.status_code == 200
    assert res.json()["ok"] is False
