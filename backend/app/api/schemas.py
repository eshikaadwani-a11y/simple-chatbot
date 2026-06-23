"""Pydantic request/response models for the API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    thread_id: str = Field(..., description="Conversation id (LangGraph thread).")
    model: str | None = Field(default=None, description="Override model from models.yaml.")


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool


class ProgressEvent(BaseModel):
    type: str = Field(..., description="topic_completed | quiz_result | goal | preference")
    topic: str | None = None
    mastery: float | None = 1.0
    score: float | None = None
    total: int | None = None
    weak_concepts: list[str] | None = None
    goal: str | None = None
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
