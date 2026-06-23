"""LangGraph multi-agent graph assembly.

Topology (see docs/ARCHITECTURE.md):

    START -> load_memory -> planner -> supervisor
          -> {tutor|quiz|roadmap|resume|interview|general}
          -> (tool calls?) -> tools -> back to the specialist   [ReAct loop]
          -> memory_update -> respond -> END

The supervisor uses conditional edges to delegate to specialists, and each
specialist uses conditional edges to drive the ReAct tool loop.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.nodes import (
    load_memory,
    make_specialist_node,
    memory_update,
    planner,
    respond,
    supervisor,
)
from app.agents.state import AgentState
from app.tools import ALL_TOOLS

_SPECIALISTS = ["tutor", "quiz", "roadmap", "resume", "interview", "general"]


def _route_from_supervisor(state: AgentState) -> str:
    """Conditional edge: send to the specialist chosen by the supervisor."""
    return state.get("route", "general")


def _after_specialist(state: AgentState) -> str:
    """ReAct decision: if the last AIMessage requested tools, run them; else finish.

    Reuses LangGraph's ``tools_condition`` which returns "tools" or END.
    """
    decision = tools_condition(state)
    return "tools" if decision == "tools" else "memory_update"


def build_graph(checkpointer=None):
    """Construct and compile the multi-agent StateGraph.

    Args:
        checkpointer: a LangGraph checkpointer for short-term memory / recovery.
    """
    graph = StateGraph(AgentState)

    # Core pipeline nodes.
    graph.add_node("load_memory", load_memory)
    graph.add_node("planner", planner)
    graph.add_node("supervisor", supervisor)
    graph.add_node("memory_update", memory_update)
    graph.add_node("respond", respond)

    # One node per specialist agent.
    for route in _SPECIALISTS:
        graph.add_node(f"agent_{route}", make_specialist_node(route))  # type: ignore[arg-type]

    # Shared tool executor (ReAct). Injected args (user_id via InjectedState)
    # are filled automatically by ToolNode.
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    # ---- Edges ----
    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "planner")
    graph.add_edge("planner", "supervisor")

    # Supervisor -> chosen specialist.
    graph.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {route: f"agent_{route}" for route in _SPECIALISTS},
    )

    # Each specialist: ReAct loop or finish.
    for route in _SPECIALISTS:
        graph.add_conditional_edges(
            f"agent_{route}",
            _after_specialist,
            {"tools": "tools", "memory_update": "memory_update"},
        )

    # After tools run, control returns to the active specialist to analyze results.
    # We route back through the supervisor's chosen specialist using the stored route.
    graph.add_conditional_edges(
        "tools",
        _route_from_supervisor,
        {route: f"agent_{route}" for route in _SPECIALISTS},
    )

    graph.add_edge("memory_update", "respond")
    graph.add_edge("respond", END)

    return graph.compile(checkpointer=checkpointer)
