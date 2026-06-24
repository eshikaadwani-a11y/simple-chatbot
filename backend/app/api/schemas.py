"""Pydantic request/response models for the API.

Input models enforce length limits, allowed value sets, and basic sanitization
(stripping control characters) as a first line of defense against malformed or
abusive input before it reaches the agent or the database.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Conversation/thread ids are generated client-side; restrict to a safe charset.
_THREAD_ID_PATTERN = r"^[A-Za-z0-9_.:-]{1,128}$"


def _strip_control_chars(text: str) -> str:
    """Remove non-printable control characters (keep tab/newline/carriage return)."""
    return "".join(ch for ch in text if ch in "\t\n\r" or ord(ch) >= 32).strip()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    thread_id: str = Field(..., pattern=_THREAD_ID_PATTERN)
    model: str | None = Field(default=None, max_length=64)

    @field_validator("message")
    @classmethod
    def _clean_message(cls, v: str) -> str:
        cleaned = _strip_control_chars(v)
        if not cleaned:
            raise ValueError("message must contain printable text")
        return cleaned


class ResumeRequest(BaseModel):
    thread_id: str = Field(..., pattern=_THREAD_ID_PATTERN)
    approved: bool


class ProgressEvent(BaseModel):
    type: Literal["topic_completed", "quiz_result", "goal", "preference"]
    topic: str | None = Field(default=None, max_length=200)
    mastery: float | None = Field(default=1.0, ge=0.0, le=1.0)
    score: float | None = Field(default=None, ge=0.0)
    total: int | None = Field(default=None, ge=0, le=1000)
    weak_concepts: list[str] | None = Field(default=None, max_length=50)
    goal: str | None = Field(default=None, max_length=300)
    preferences: dict[str, Any] | None = None


class UserResponse(BaseModel):
    user_id: str
    email: str | None = None


class AnalyticsResponse(BaseModel):
    user_id: str
    xp: int
    streak_days: int
    topics_completed: int
    quizzes_taken: int
    average_quiz_score: float | None = None
    weak_areas: list[str] = []
    goals: list[str] = []
