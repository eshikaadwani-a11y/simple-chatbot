"""Notes generator tool — structured study notes."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from app.tools._llm_helper import generate_json

_SYSTEM = (
    "You are an expert note-taker. Produce clear, well-structured study notes that "
    "aid retention: hierarchical outline, key definitions, examples, and a recap."
)


@tool
def notes_generator(topic: str, style: str = "outline", depth: str = "standard") -> str:
    """Generate structured study notes for a topic.

    Args:
        topic: subject to take notes on.
        style: outline | cornell | cheatsheet.
        depth: brief | standard | deep.

    Returns JSON: {topic, style, sections:[{heading, points[]}], key_terms:[{term,
    definition}], summary, review_questions[]}.
    """
    prompt = (
        f"Topic: {topic}\nStyle: {style}\nDepth: {depth}.\n"
        "Produce hierarchical sections, key terms with definitions, a concise "
        "summary, and 3-5 active-recall review questions."
    )
    data = generate_json(_SYSTEM, prompt)
    data.setdefault("topic", topic)
    data.setdefault("style", style)
    return json.dumps(data)
