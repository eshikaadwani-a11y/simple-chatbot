"""Agent runtime — compiled graph singleton + streaming helpers.

The graph is compiled once with a durable checkpointer and reused across
requests. Each conversation maps to a LangGraph ``thread_id`` (short-term memory
+ workflow recovery). This module also exposes a token-streaming generator that
the FastAPI SSE endpoint consumes.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import HumanMessage

from app.agents.graph import build_graph
from app.analytics import TokenUsageCallback, record_run_usage
from app.memory.checkpointer import create_checkpointer

logger = logging.getLogger("learngraph")

_GRAPH = None


async def init_graph():
    """Compile the graph with an async-capable checkpointer (call once at startup)."""
    global _GRAPH
    from app.memory.checkpointer import create_async_checkpointer

    _GRAPH = build_graph(checkpointer=await create_async_checkpointer())
    logger.info("Multi-agent graph compiled.")
    return _GRAPH


async def shutdown():
    """Release resources (connection pools) at shutdown."""
    from app.memory.checkpointer import close_pools

    await close_pools()


def get_graph():
    """Return the compiled graph.

    In production the graph is built during startup via ``init_graph`` with an
    async Postgres checkpointer. This lazy fallback (used by tests / scripts that
    don't run the FastAPI lifespan) builds with the in-memory saver.
    """
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph(checkpointer=create_checkpointer())
        logger.info("Multi-agent graph compiled (lazy fallback).")
    return _GRAPH


def _config(user_id: str, thread_id: str, callbacks: list | None = None) -> dict[str, Any]:
    # Namespace the thread by user id so a user can never read or resume another
    # user's conversation state, even if they guess/learn the raw thread id.
    namespaced = f"{user_id}::{thread_id}"
    config: dict[str, Any] = {
        "configurable": {"thread_id": namespaced, "user_id": user_id},
        # LangSmith trace enrichment: a stable run name, tags, and metadata make
        # traces filterable by user/thread in the LangSmith UI.
        "run_name": "learngraph-agent",
        "tags": ["learngraph", f"user:{user_id}"],
        "metadata": {"user_id": user_id, "thread_id": thread_id},
    }
    if callbacks:
        config["callbacks"] = callbacks
    return config


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
    usage_cb = TokenUsageCallback()
    config = _config(user_id, thread_id, callbacks=[usage_cb])

    seen_route = False
    try:
        async for event in graph.astream_events(inputs, config=config, version="v2"):
            kind = event.get("event")
            node = (event.get("metadata") or {}).get("langgraph_node", "")

            if kind == "on_chat_model_stream" and node.startswith("agent_"):
                # Only stream tokens from specialist agents — never the planner
                # or supervisor (whose output is internal routing, not the answer).
                chunk = event["data"].get("chunk")
                text = getattr(chunk, "content", None)
                if text:
                    yield {"type": "token", "content": text}

            elif kind == "on_tool_start":
                yield {"type": "tool", "name": event.get("name", "tool")}

            elif kind == "on_chain_end" and not seen_route and node == "supervisor":
                out = event.get("data", {}).get("output") or {}
                if isinstance(out, dict) and out.get("route"):
                    seen_route = True
                    yield {"type": "route", "route": out["route"]}

        # Single state read: surface interrupts AND capture the route for analytics.
        snapshot = await graph.aget_state(config)
        route = (getattr(snapshot, "values", {}) or {}).get("route")

        # Record usage/cost (best-effort, off the event loop).
        try:
            await asyncio.to_thread(record_run_usage, user_id, route, usage_cb)
        except Exception as exc:  # noqa: BLE001
            logger.debug("usage recording failed: %s", exc)

        for payload in _interrupts_from(snapshot):
            yield {"type": "interrupt", "payload": payload}
    except Exception as exc:  # noqa: BLE001
        logger.exception("stream_response failed")
        yield {"type": "error", "content": str(exc)}

    yield {"type": "done"}


def _interrupts_from(snapshot) -> list[Any]:
    """Extract interrupt payloads from a graph state snapshot."""
    if not getattr(snapshot, "next", None):
        return []
    payloads: list[Any] = []
    for task in getattr(snapshot, "tasks", []) or []:
        for itr in getattr(task, "interrupts", []) or []:
            payloads.append(getattr(itr, "value", itr))
    return payloads


async def _pending_interrupts(graph, config: dict[str, Any]) -> list[Any]:
    """Return the payloads of any interrupts the run is currently paused on.

    Uses the async state API (``aget_state``) because the graph runs with an
    async checkpointer in production.
    """
    snapshot = await graph.aget_state(config)
    return _interrupts_from(snapshot)


async def resume_after_approval(
    *, user_id: str, thread_id: str, approved: bool
) -> AsyncIterator[dict[str, Any]]:
    """Resume an interrupted (HITL) run once the user approves/rejects."""
    from langgraph.types import Command

    graph = get_graph()
    config = _config(user_id, thread_id)

    # Guard: only resume if the run is actually paused on an interrupt for this
    # thread. Resuming an un-paused thread would raise / corrupt state.
    if not await _pending_interrupts(graph, config):
        yield {"type": "error", "content": "No pending approval for this conversation."}
        yield {"type": "done"}
        return

    try:
        async for event in graph.astream_events(
            Command(resume={"approved": approved}), config=config, version="v2"
        ):
            node = (event.get("metadata") or {}).get("langgraph_node", "")
            if event.get("event") == "on_chat_model_stream" and node.startswith("agent_"):
                chunk = event["data"].get("chunk")
                text = getattr(chunk, "content", None)
                if text:
                    yield {"type": "token", "content": text}
        yield {"type": "resumed", "approved": approved}
    except Exception as exc:  # noqa: BLE001
        logger.exception("resume_after_approval failed")
        yield {"type": "error", "content": str(exc)}
    yield {"type": "done"}
