"""Shared graph state.

``AgentState`` flows through every node. ``messages`` uses the ``add_messages``
reducer so each node can append without clobbering history (enabling the
ReAct tool loop and multi-turn memory).
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages

Route = Literal["tutor", "quiz", "roadmap", "resume", "interview", "general"]


class AgentState(TypedDict, total=False):
    # Conversation (reduced/append-only).
    messages: Annotated[list, add_messages]

    # Identity + memory.
    user_id: str
    memory_context: dict[str, Any]  # long-term snapshot loaded at run start

    # Planner / supervisor outputs.
    plan: str
    route: Route

    # Human-in-the-loop.
    pending_action: dict[str, Any] | None
    approved: bool | None

    # Bookkeeping for the analysis/memory nodes.
    tool_invocations: list[str]
