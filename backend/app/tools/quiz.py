"""Quiz generator tool — adaptive quizzes with an answer key."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from app.tools._llm_helper import generate_json

_SYSTEM = (
    "You are an assessment designer. Create fair, unambiguous quiz questions that "
    "test conceptual understanding, not trivia. Calibrate difficulty as requested."
)


@tool
def quiz_generator(topic: str, num_questions: int = 5, difficulty: str = "medium") -> str:
    """Generate an adaptive quiz for a topic with an answer key for auto-grading.

    Args:
        topic: subject of the quiz.
        num_questions: how many questions.
        difficulty: easy | medium | hard (adapt to the learner's level).

    Returns JSON: {topic, difficulty, questions:[{id, type, prompt, options[],
    answer, explanation, concept}]}. `type` is "mcq" or "short".
    """
    prompt = (
        f"Topic: {topic}\nNumber of questions: {num_questions}\nDifficulty: {difficulty}.\n"
        "Mix multiple-choice (type=mcq with options and a single correct answer) and "
        "short-answer (type=short). Include a one-line explanation and the underlying "
        "concept for each so weak areas can be detected."
    )
    data = generate_json(_SYSTEM, prompt)
    data.setdefault("topic", topic)
    data.setdefault("difficulty", difficulty)
    return json.dumps(data)
