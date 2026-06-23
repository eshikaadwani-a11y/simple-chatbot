"""Graph nodes: load_memory, planner, supervisor, specialist agent, memory_update.

Each node takes the current ``AgentState`` and returns a partial state update.
"""
from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.types import interrupt

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

# Routes whose results are persisted and therefore gated behind human approval.
HIGH_IMPACT_ROUTES: set[str] = {"roadmap", "resume"}


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


def human_approval(state: AgentState) -> dict:
    """Human-in-the-loop checkpoint for high-impact actions.

    Calls LangGraph's ``interrupt()``, which pauses the run and persists state
    via the checkpointer. The API surfaces the payload to the user; once they
    decide, the run is resumed with ``Command(resume={"approved": bool})`` and
    execution continues from exactly here (workflow recovery).
    """
    route = state.get("route")
    decision = interrupt(
        {
            "action": f"persist_{route}_result",
            "route": route,
            "message": f"Approve saving this {route} result to your learner profile?",
        }
    )
    if isinstance(decision, dict):
        approved = bool(decision.get("approved"))
    else:
        approved = bool(decision)
    logger.info("Human approval for %s: %s", route, approved)
    return {"approved": approved}


def _persist_route_result(user_id: str, state: AgentState) -> None:
    """Persist an approved high-impact result (e.g. a generated roadmap)."""
    if state.get("route") != "roadmap" or not state.get("approved"):
        return
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "roadmap_generator":
            try:
                plan = json.loads(msg.content)
                long_term.save_roadmap(user_id, plan.get("goal", ""), plan)
                long_term.award_xp(user_id, 30)
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning("Could not persist roadmap: %s", exc)
            return


def memory_update(state: AgentState) -> dict:
    """Persist durable facts gleaned from this turn (best-effort)."""
    user_id = state.get("user_id", "anonymous")
    try:
        # Persist approved high-impact results first.
        _persist_route_result(user_id, state)

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
