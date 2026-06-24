"""Shared test fixtures.

The whole suite runs with **no external services**: Supabase, Postgres, and the
LLM are all absent/mocked. The app is designed to fall back to in-memory stores,
and tests patch the chat model with a deterministic fake.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage


class FakeLLM:
    """A deterministic stand-in for a chat model.

    It inspects the system prompt to decide which graph node is calling it:
      * Planner  -> returns a short plan.
      * Supervisor -> returns the configured route word.
      * Specialist -> returns a fixed answer (never requests tools).

    Supports ``bind_tools`` (returns self) so specialist nodes work unchanged.
    """

    def __init__(self, route: str = "general", answer: str = "Here is your answer."):
        self.route = route
        self.answer = answer

    def bind_tools(self, tools, **kwargs):  # noqa: ANN001, ARG002
        return self

    def invoke(self, messages, *args, **kwargs):  # noqa: ANN001, ARG002
        system = ""
        if messages and isinstance(getattr(messages[0], "content", None), str):
            system = messages[0].content
        if "Planner" in system:
            return AIMessage(content="Plan: 1) understand goal 2) respond")
        if "Supervisor" in system:
            return AIMessage(content=self.route)
        return AIMessage(content=self.answer)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Ensure no real services are configured and caches are reset per test."""
    for key in (
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_JWT_SECRET",
        "DATABASE_URL",
        "TAVILY_API_KEY",
        "YOUTUBE_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    from app.config import get_settings
    from app.db import supabase_client

    get_settings.cache_clear()
    supabase_client.get_supabase.cache_clear()
    yield
    get_settings.cache_clear()
    supabase_client.get_supabase.cache_clear()


@pytest.fixture(autouse=True)
def clear_memory_store():
    """Reset the in-memory long-term store between tests."""
    from app.memory import long_term

    long_term._MEM.clear()
    yield
    long_term._MEM.clear()


@pytest.fixture
def fake_llm(monkeypatch):
    """Patch the chat model used by graph nodes with a deterministic fake."""

    def _install(route: str = "general", answer: str = "Here is your answer.") -> FakeLLM:
        llm = FakeLLM(route=route, answer=answer)
        monkeypatch.setattr("app.agents.nodes.get_chat_model", lambda *a, **k: llm)
        return llm

    return _install
