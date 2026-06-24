"""Usage analytics, cost estimation, token callback, and admin endpoint tests."""

from __future__ import annotations

import types

import pytest
from fastapi.testclient import TestClient

from app import analytics
from app.analytics import TokenUsageCallback, aggregate_admin, estimate_cost, record_usage
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_events():
    analytics._EVENTS.clear()
    yield
    analytics._EVENTS.clear()


def test_estimate_cost_matches_by_prefix():
    # gpt-5: $1.25 / $10 per 1M tokens.
    cost = estimate_cost("gpt-5-2025-08-01", 1_000_000, 1_000_000)
    assert round(cost, 2) == round(1.25 + 10.0, 2)


def test_estimate_cost_unknown_model_is_zero():
    assert estimate_cost("mystery-model", 1000, 1000) == 0.0
    assert estimate_cost(None, 1000, 1000) == 0.0


def test_token_callback_accumulates_usage_metadata():
    msg = types.SimpleNamespace(
        usage_metadata={"input_tokens": 10, "output_tokens": 5},
        response_metadata={"model_name": "gpt-5"},
    )
    gen = types.SimpleNamespace(message=msg)
    resp = types.SimpleNamespace(llm_output={"model_name": "gpt-5"}, generations=[[gen]])

    cb = TokenUsageCallback()
    cb.on_llm_end(resp)
    cb.on_tool_start({"name": "web_search"}, "q")

    assert cb.prompt_tokens == 10
    assert cb.completion_tokens == 5
    assert cb.model == "gpt-5"
    assert cb.tools_used == ["web_search"]


def test_record_usage_and_aggregate():
    record_usage(
        user_id="u1",
        event_type="chat",
        agent="roadmap",
        model="gpt-5",
        prompt_tokens=100,
        completion_tokens=50,
    )
    record_usage(user_id="u1", event_type="tool", agent="roadmap", tool="roadmap_generator")
    record_usage(user_id="u1", event_type="chat", agent="quiz", model="gpt-5")
    record_usage(user_id="u1", event_type="resume_analysis")

    agg = aggregate_admin()
    assert agg["ai_requests"] == 2
    assert agg["tool_calls"] == 1
    assert agg["resume_analyses"] == 1
    assert agg["roadmaps_generated"] == 1
    assert agg["quiz_attempts"] == 1
    assert agg["tokens_total"] == 150
    assert agg["cost_total_usd"] > 0
    assert ("roadmap", 1) in agg["top_agents"]


def test_admin_endpoint_accessible_in_dev_mode():
    # No ADMIN_EMAILS + non-production => allowed (dev convenience).
    res = client.get("/admin/analytics")
    assert res.status_code == 200
    body = res.json()
    assert "ai_requests" in body and "cost_total_usd" in body
