"""Roadmap generator tool — dependency-ordered learning plans."""
from __future__ import annotations

import json

from langchain_core.tools import tool

from app.tools._llm_helper import generate_json

_SYSTEM = (
    "You are an expert curriculum designer. Build a realistic, dependency-ordered "
    "learning roadmap. Order topics so prerequisites come first."
)


@tool
def roadmap_generator(goal: str, current_level: str = "beginner", weeks: int = 8) -> str:
    """Generate a personalized, dependency-ordered learning roadmap for a goal.

    Args:
        goal: what the learner wants to achieve (e.g. "become a backend engineer").
        current_level: beginner | intermediate | advanced.
        weeks: target duration.

    Returns JSON: {goal, level, weeks, milestones:[{week, title, topics[],
    outcomes[], resources_hint}], prerequisites_graph:[{topic, depends_on[]}]}.
    """
    prompt = (
        f"Goal: {goal}\nCurrent level: {current_level}\nDuration: {weeks} weeks.\n"
        "Produce milestones (one or more per week), each with topics, measurable "
        "outcomes, and a prerequisites_graph capturing topic dependencies."
    )
    data = generate_json(_SYSTEM, prompt)
    data.setdefault("goal", goal)
    data.setdefault("level", current_level)
    data.setdefault("weeks", weeks)
    return json.dumps(data)
