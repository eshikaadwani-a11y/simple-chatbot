"""Interview preparation tool — questions, mock interviews, and rubrics."""
from __future__ import annotations

import json

from langchain_core.tools import tool

from app.tools._llm_helper import generate_json

_SYSTEM = (
    "You are an experienced interviewer at a top tech company. Produce realistic "
    "interview questions with evaluation rubrics and model answer outlines."
)


@tool
def interview_prep(
    role: str,
    interview_type: str = "mixed",
    num_questions: int = 6,
    seniority: str = "entry",
) -> str:
    """Generate interview questions and a grading rubric for a mock interview.

    Args:
        role: target role (e.g. "Backend Engineer").
        interview_type: technical | behavioral | system_design | mixed.
        num_questions: how many questions.
        seniority: entry | mid | senior.

    Returns JSON: {role, type, questions:[{id, category, question,
    what_good_looks_like, follow_ups[], rubric}]}.
    """
    prompt = (
        f"Role: {role}\nInterview type: {interview_type}\nSeniority: {seniority}\n"
        f"Number of questions: {num_questions}.\n"
        "For each question include the category, what a strong answer covers, "
        "two follow-up probes, and a concise scoring rubric."
    )
    data = generate_json(_SYSTEM, prompt)
    data.setdefault("role", role)
    data.setdefault("type", interview_type)
    return json.dumps(data)
