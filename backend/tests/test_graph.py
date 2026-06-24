"""Integration tests for the compiled multi-agent graph, incl. routing + HITL."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agents.graph import build_graph
from tests.conftest import FakeLLM


def _build(monkeypatch, route, answer="Done."):
    llm = FakeLLM(route=route, answer=answer)
    monkeypatch.setattr("app.agents.nodes.get_chat_model", lambda *a, **k: llm)
    return build_graph(checkpointer=MemorySaver())


def _config(thread="t1", user="u1"):
    return {"configurable": {"thread_id": thread, "user_id": user}}


def test_non_high_impact_route_finishes_without_interrupt(monkeypatch):
    graph = _build(monkeypatch, route="quiz", answer="Here is your quiz.")
    cfg = _config()
    graph.invoke({"messages": [HumanMessage("quiz me on graphs")], "user_id": "u1"}, cfg)

    state = graph.get_state(cfg)
    assert state.values["route"] == "quiz"
    # No interrupt -> run reached the end.
    assert not state.next
    last = state.values["messages"][-1]
    assert isinstance(last, AIMessage)


def test_high_impact_route_pauses_for_human_approval(monkeypatch):
    graph = _build(monkeypatch, route="roadmap", answer="Proposed roadmap.")
    cfg = _config(thread="t2")
    graph.invoke({"messages": [HumanMessage("make me a roadmap")], "user_id": "u1"}, cfg)

    state = graph.get_state(cfg)
    # Paused at the human approval node.
    assert "human_approval" in state.next
    interrupts = [itr for task in state.tasks for itr in (task.interrupts or [])]
    assert interrupts, "expected a pending interrupt payload"


def test_resume_after_approval_sets_flag_and_completes(monkeypatch):
    graph = _build(monkeypatch, route="resume", answer="Resume feedback.")
    cfg = _config(thread="t3")
    graph.invoke({"messages": [HumanMessage("review my resume")], "user_id": "u1"}, cfg)
    assert "human_approval" in graph.get_state(cfg).next

    graph.invoke(Command(resume={"approved": True}), cfg)
    final = graph.get_state(cfg)
    assert not final.next
    assert final.values["approved"] is True
