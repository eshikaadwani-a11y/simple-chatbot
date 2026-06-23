"""Graph nodes: load_memory, planner, supervisor, specialist agent, memory_update.

Each node takes the current ``AgentState`` and returns a partial state update.
"""
from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.models import get_chat_model
from app.agents.prompts import (
    PLANNER_PROMPT,
    SUPERVISOR_PROMPT,
    specialist_system_prompt,
)
from app.agents.state import AgentState, Route
from app.memory import long_term
from app.tools import TOOLS_BY_AGENT

logger = logging.getLogger("learngraph")

_VALID_ROUTES: set[str] = {"tutor", "quiz", "roadmap", "resume", "interview", "general"}


def load_memory(state: AgentState) -> dict:
    """Hydrate the graph with the learner's long-term memory at run start."""
    user_id = state.get("user_id", "anonymous")
    try:
        context = long_term.load_memory_context(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load memory for %s: %s", user_id, exc)
        context = {}
    return {"memory_context": context, "tool_invocations": []}


def planner(state: AgentState) -> dict:
    """Produce a short internal plan for the latest request."""
    llm = get_chat_model()
    msgs = [SystemMessage(content=PLANNER_PROMPT), *state["messages"]]
    resp = llm.invoke(msgs)
    plan = resp.content if isinstance(resp.content, str) else str(resp.content)
    return {"plan": plan.strip()}


def supervisor(state: AgentState) -> dict:
    """Classify the request and choose a specialist (conditional routing)."""
    llm = get_chat_model()
    msgs = [SystemMessage(content=SUPERVISOR_PROMPT), *state["messages"]]
    resp = llm.invoke(msgs)
    raw = (resp.content if isinstance(resp.content, str) else str(resp.content)).strip().lower()
    match = re.search(r"tutor|quiz|roadmap|resume|interview|general", raw)
    route: Route = match.group(0) if match else "general"  # type: ignore[assignment]
    logger.info("Supervisor routed to: %s", route)
    return {"route": route}


def make_specialist_node(route: Route):
    """Build a specialist agent node bound to that specialist's tools.

    The node is a single ReAct step: the model reasons and either emits tool
    calls (looped back via the ToolNode) or produces the final answer.
    """
    tools = TOOLS_BY_AGENT.get(route, TOOLS_BY_AGENT["general"])

    def specialist(state: AgentState) -> dict:
        llm = get_chat_model().bind_tools(tools)
        system = specialist_system_prompt(route, state.get("memory_context", {}))
        plan = state.get("plan")
        if plan:
            system += f"\n\nInternal plan to follow:\n{plan}"
        msgs = [SystemMessage(content=system), *state["messages"]]
        resp = llm.invoke(msgs)
        return {"messages": [resp]}

    specialist.__name__ = f"agent_{route}"
    return specialist


def memory_update(state: AgentState) -> dict:
    """Persist durable facts gleaned from this turn (best-effort)."""
    user_id = state.get("user_id", "anonymous")
    try:
        # Award a small amount of XP for engagement; specific tools award more.
        long_term.award_xp(user_id, 5)

        # Heuristic goal capture from the latest human message.
        last_human = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), None
        )
        if last_human and isinstance(last_human.content, str):
            text = last_human.content.lower()
            if any(k in text for k in ("i want to", "my goal", "learn to", "become a")):
                long_term.add_goal(user_id, last_human.content.strip()[:200])
    except Exception as exc:  # noqa: BLE001
        logger.warning("memory_update failed for %s: %s", user_id, exc)
    return {}


def respond(state: AgentState) -> dict:
    """Terminal node. The final AIMessage already holds the answer; this is a
    seam for post-processing (e.g. citations, safety) if needed later."""
    return {}
