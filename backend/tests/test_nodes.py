"""Unit tests for individual graph nodes (planner, supervisor, memory_update)."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agents import nodes
from app.memory import long_term
from tests.conftest import FakeLLM


def _patch_llm(monkeypatch, route="general", answer="ok"):
    llm = FakeLLM(route=route, answer=answer)
    monkeypatch.setattr("app.agents.nodes.get_chat_model", lambda *a, **k: llm)
    return llm


def test_load_memory_resets_approval_flag(monkeypatch):
    out = nodes.load_memory({"user_id": "u1", "approved": True})
    assert out["approved"] is None
    assert out["pending_action"] is None
    assert "memory_context" in out


def test_planner_produces_plan(monkeypatch):
    _patch_llm(monkeypatch)
    out = nodes.planner({"messages": [HumanMessage("teach me trees")]})
    assert isinstance(out["plan"], str) and out["plan"]


def test_supervisor_routes_to_configured_specialist(monkeypatch):
    _patch_llm(monkeypatch, route="roadmap")
    out = nodes.supervisor({"messages": [HumanMessage("build a roadmap")]})
    assert out["route"] == "roadmap"


def test_supervisor_defaults_to_general_on_unknown(monkeypatch):
    _patch_llm(monkeypatch, route="something-weird")
    out = nodes.supervisor({"messages": [HumanMessage("hi")]})
    assert out["route"] == "general"


def test_specialist_node_returns_message(monkeypatch):
    _patch_llm(monkeypatch, answer="Final tutor answer.")
    node = nodes.make_specialist_node("tutor")
    out = node({"messages": [HumanMessage("explain hashing")], "memory_context": {}})
    assert isinstance(out["messages"][0], AIMessage)
    assert out["messages"][0].content == "Final tutor answer."


def test_memory_update_persists_approved_roadmap():
    plan = {"goal": "Backend mastery", "milestones": []}
    state = {
        "user_id": "u1",
        "route": "roadmap",
        "approved": True,
        "messages": [
            HumanMessage("make a roadmap"),
            ToolMessage(content=json.dumps(plan), name="roadmap_generator", tool_call_id="t1"),
        ],
    }
    nodes.memory_update(state)
    roadmaps = long_term.get_roadmaps("u1")
    assert len(roadmaps) == 1
    assert roadmaps[0]["goal"] == "Backend mastery"


def test_memory_update_does_not_persist_when_not_approved():
    state = {
        "user_id": "u1",
        "route": "roadmap",
        "approved": False,
        "messages": [
            ToolMessage(content="{}", name="roadmap_generator", tool_call_id="t1"),
        ],
    }
    nodes.memory_update(state)
    assert long_term.get_roadmaps("u1") == []


def test_memory_update_captures_goal_from_message():
    state = {
        "user_id": "u1",
        "route": "tutor",
        "approved": None,
        "messages": [HumanMessage("I want to become a backend engineer")],
    }
    nodes.memory_update(state)
    goals = long_term.get_learner_profile("u1")["goals"]
    assert any("backend engineer" in g for g in goals)
