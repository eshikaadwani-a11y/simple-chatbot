"""Resume review tool — ATS-style analysis and improvement suggestions."""
from __future__ import annotations

import json

from langchain_core.tools import tool

from app.tools._llm_helper import generate_json

_SYSTEM = (
    "You are a senior technical recruiter and ATS expert. Analyze resumes for "
    "impact, clarity, quantified achievements, keyword coverage, and ATS parseability. "
    "Be specific and actionable; never invent experience the candidate doesn't have."
)


@tool
def resume_review(resume_text: str, target_role: str = "Software Engineer") -> str:
    """Analyze a resume against a target role and return structured feedback.

    Args:
        resume_text: the full plain-text resume.
        target_role: role the candidate is targeting.

    Returns JSON: {ats_score (0-100), strengths[], weaknesses[],
    missing_keywords[], bullet_rewrites:[{before, after}], summary}.
    """
    prompt = (
        f"Target role: {target_role}\n\nResume:\n'''\n{resume_text[:8000]}\n'''\n\n"
        "Score ATS-friendliness 0-100, list strengths and weaknesses, identify "
        "missing role-relevant keywords, and rewrite up to 5 weak bullets into "
        "quantified, impact-driven versions (before/after)."
    )
    data = generate_json(_SYSTEM, prompt)
    data.setdefault("target_role", target_role)
    return json.dumps(data)
