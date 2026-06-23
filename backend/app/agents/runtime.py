"""Agent runtime — compiled graph singleton + streaming helpers.

The graph is compiled once with a durable checkpointer and reused across
requests. Each conversation maps to a LangGraph ``thread_id`` (short-term memory
+ workflow recovery). This module also exposes a token-streaming generator that
the FastAPI SSE endpoint consumes.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from langchain_core.messages import HumanMessage

from app.agents.graph import build_graph
from app.memory.checkpointer import create_checkpointer

logger = logging.getLogger("learngraph")

_GRAPH = None


def get_graph():
    """Lazily compile and cache the multi-agent graph."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph(checkpointer=create_checkpointer())
        logger.info("Multi-agent graph compiled.")
    return _GRAPH


def _config(user_id: str, thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id, "user_id": user_id}}


async def stream_response(
    *, user_id: str, thread_id: str, message: str
) -> AsyncIterator[dict[str, Any]]:
    """Stream the agent run as a sequence of typed events.

    Yields dicts shaped for SSE:
      {"type": "token", "content": str}     # incremental answer tokens
      {"type": "route", "route": str}       # which specialist was chosen
      {"type": "tool", "name": str}         # a tool was invoked
      {"type": "interrupt", "payload": ...} # human-in-the-loop pause
      {"type": "done"}                      # end of stream
    """
    graph = get_graph()
    inputs = {"messages": [HumanMessage(content=message)], "user_id": user_id}
    config = _config(user_id, thread_id)

    seen_route = False
    try:
        async for event in graph.astream_events(inputs, config=config, version="v2"):
            kind = event.get("event")

            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                text = getattr(chunk, "content", None)
                if text:
                    yield {"type": "token", "content": text}

            elif kind == "on_tool_start":
                yield {"type": "tool", "name": event.get("name", "tool")}

            elif kind == "on_chain_end" and not seen_route:
                # Surface the supervisor's routing decision once available.
                out = event.get("data", {}).get("output") or {}
                if isinstance(out, dict) and out.get("route"):
                    seen_route = True
                    yield {"type": "route", "route": out["route"]}

        # Detect a human-in-the-loop interrupt left in the persisted state.
        snapshot = graph.get_state(config)
        if getattr(snapshot, "next", None):
            pending = snapshot.values.get("pending_action")
            if pending:
                yield {"type": "interrupt", "payload": pending}
    except Exception as exc:  # noqa: BLE001
        logger.exception("stream_response failed")
        yield {"type": "error", "content": str(exc)}

    yield {"type": "done"}


async def resume_after_approval(
    *, user_id: str, thread_id: str, approved: bool
) -> AsyncIterator[dict[str, Any]]:
    """Resume an interrupted (HITL) run once the user approves/rejects."""
    from langgraph.types import Command

    graph = get_graph()
    config = _config(user_id, thread_id)
    try:
        async for event in graph.astream_events(
            Command(resume={"approved": approved}), config=config, version="v2"
        ):
            if event.get("event") == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                text = getattr(chunk, "content", None)
                if text:
                    yield {"type": "token", "content": text}
    except Exception as exc:  # noqa: BLE001
        logger.exception("resume_after_approval failed")
        yield {"type": "error", "content": str(exc)}
    yield {"type": "done"}
