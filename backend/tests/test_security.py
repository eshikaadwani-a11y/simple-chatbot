"""Security tests: headers, rate limiting, input validation, env validation."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.schemas import ChatRequest, ProgressEvent
from app.config import Settings
from app.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    register_error_handlers,
    validate_environment,
)


def _app(per_minute=1000, heavy=1000) -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, per_minute=per_minute, heavy_per_minute=heavy)
    register_error_handlers(app)

    @app.get("/x")
    async def x():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/chat/test")
    async def chat():
        return {"ok": True}

    return app


def test_security_headers_present():
    client = TestClient(_app())
    res = client.get("/x")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" in res.headers
    assert "Content-Security-Policy" in res.headers


def test_rate_limit_blocks_after_threshold():
    client = TestClient(_app(per_minute=3))
    statuses = [client.get("/x").status_code for _ in range(5)]
    assert statuses.count(200) == 3
    assert 429 in statuses


def test_health_is_exempt_from_rate_limit():
    client = TestClient(_app(per_minute=1))
    assert all(client.get("/health").status_code == 200 for _ in range(5))


def test_heavy_paths_use_tighter_budget():
    client = TestClient(_app(per_minute=1000, heavy=2))
    statuses = [client.post("/chat/test").status_code for _ in range(4)]
    assert statuses.count(200) == 2
    assert 429 in statuses


# ---- input validation ----
def test_chat_request_rejects_bad_thread_id():
    with pytest.raises(ValueError):
        ChatRequest(message="hi", thread_id="bad id with spaces!!")


def test_chat_request_strips_control_chars():
    req = ChatRequest(message="hello\x00\x07 world", thread_id="thread-1")
    assert "\x00" not in req.message and "world" in req.message


def test_progress_event_rejects_unknown_type():
    with pytest.raises(ValueError):
        ProgressEvent(type="not_a_real_event")


def test_progress_event_rejects_out_of_range_mastery():
    with pytest.raises(ValueError):
        ProgressEvent(type="topic_completed", topic="x", mastery=5.0)


# ---- env validation ----
def test_validate_environment_raises_in_prod_when_missing():
    with pytest.raises(RuntimeError):
        validate_environment(Settings(environment="production"))


def test_validate_environment_warns_in_dev(caplog):
    # Should not raise in development even with everything missing.
    validate_environment(Settings(environment="development"))
