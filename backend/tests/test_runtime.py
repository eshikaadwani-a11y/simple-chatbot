"""Runtime helper tests (thread namespacing + resume guard)."""

from __future__ import annotations

import pytest

from app.agents import runtime


def test_thread_id_is_namespaced_by_user():
    cfg = runtime._config("user-a", "conv-1")
    assert cfg["configurable"]["thread_id"] == "user-a::conv-1"
    assert cfg["configurable"]["user_id"] == "user-a"
    # Different users cannot collide on the same conversation id.
    other = runtime._config("user-b", "conv-1")
    assert other["configurable"]["thread_id"] != cfg["configurable"]["thread_id"]


@pytest.mark.asyncio
async def test_resume_without_pending_interrupt_returns_error():
    events = [
        e
        async for e in runtime.resume_after_approval(
            user_id="u1", thread_id="nonexistent-thread", approved=True
        )
    ]
    types = [e["type"] for e in events]
    assert "error" in types
    assert types[-1] == "done"
