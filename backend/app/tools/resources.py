"""Resource recommendation tool — books, courses, articles, practice sets."""
from __future__ import annotations

import json

from langchain_core.tools import tool

from app.tools._llm_helper import generate_json

_SYSTEM = (
    "You are a learning resource curator. Recommend reputable, well-known resources "
    "across formats. Prefer canonical, widely-recommended materials and be honest "
    "about difficulty. Do not fabricate URLs; give titles/authors the learner can search."
)


@tool
def resource_recommender(topic: str, level: str = "beginner", formats: str = "all") -> str:
    """Recommend curated learning resources for a topic.

    Args:
        topic: subject area.
        level: beginner | intermediate | advanced.
        formats: all | books | courses | articles | practice.

    Returns JSON: {topic, level, books[], courses[], articles[], practice[]},
    each item {title, author_or_provider, why, difficulty}.
    """
    prompt = (
        f"Topic: {topic}\nLevel: {level}\nFormats requested: {formats}.\n"
        "Recommend the most respected resources. For each, explain in one line why "
        "it's worth the learner's time and note its difficulty."
    )
    data = generate_json(_SYSTEM, prompt)
    data.setdefault("topic", topic)
    data.setdefault("level", level)
    return json.dumps(data)
