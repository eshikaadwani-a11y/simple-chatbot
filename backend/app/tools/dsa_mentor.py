"""DSA mentor tool — explanations, hints (not full solutions), practice plans."""
from __future__ import annotations

import json

from langchain_core.tools import tool

from app.tools._llm_helper import generate_json

_SYSTEM = (
    "You are a patient Data Structures & Algorithms mentor. Teach for understanding. "
    "When asked for help on a problem, give progressive HINTS and the approach, plus "
    "complexity analysis — do NOT dump a full solution unless explicitly asked."
)


@tool
def dsa_mentor(topic_or_problem: str, mode: str = "explain") -> str:
    """Mentor a learner on Data Structures & Algorithms.

    Args:
        topic_or_problem: a DSA topic (e.g. "sliding window") or a problem statement.
        mode: explain | hints | practice_plan.

    Returns JSON. For explain: {topic, intuition, key_ideas[], complexity,
    common_pitfalls[], example}. For hints: {progressive_hints[], approach,
    complexity}. For practice_plan: {topic, problems:[{name, difficulty, pattern}]}.
    """
    prompt = (
        f"Mode: {mode}\nInput: {topic_or_problem}\n"
        "Follow the JSON shape described for this mode. For hints, order them from "
        "gentle nudge to near-complete approach without giving final code."
    )
    data = generate_json(_SYSTEM, prompt)
    data.setdefault("mode", mode)
    return json.dumps(data)
