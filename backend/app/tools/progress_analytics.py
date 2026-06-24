"""Progress analytics tool — XP, streaks, and mastery from stored learner data.

``user_id`` is injected from the graph state via LangGraph's ``InjectedState`` so
the LLM never sees or chooses it; the agent can only analyze the authenticated
user's own data. ``ToolNode`` fills the injected argument automatically.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState


@tool
def progress_analytics(
    focus: str = "overview",
    state: Annotated[dict[str, Any], InjectedState] = None,  # type: ignore[assignment]
) -> str:
    """Analyze the learner's stored progress (XP, streaks, mastery, weak areas).

    Args:
        focus: overview | weak_areas | streak | mastery.

    Returns JSON with computed analytics derived from quiz results, completed
    topics, and roadmap progress.
    """
    from app.memory.long_term import compute_analytics

    user_id = (state or {}).get("user_id")
    if not user_id:
        return json.dumps({"error": "no authenticated user in context"})
    try:
        return json.dumps(compute_analytics(user_id=user_id, focus=focus))
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc), "user_id": user_id, "focus": focus})
