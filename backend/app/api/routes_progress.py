"""Progress routes — analytics summary and learning-event recording."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_current_user
from app.api.schemas import AnalyticsResponse, ProgressEvent
from app.memory import long_term

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/summary", response_model=AnalyticsResponse)
async def summary(user: CurrentUser = Depends(get_current_user)) -> AnalyticsResponse:
    """Dashboard data: XP, streak, mastery, weak areas, goals."""
    stats = long_term.compute_analytics(user_id=user.user_id, focus="overview")
    return AnalyticsResponse(**stats)


@router.post("/event")
async def record_event(
    body: ProgressEvent, user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Record a learning event (topic completion, quiz result, goal, preference)."""
    uid = user.user_id
    if body.type == "topic_completed" and body.topic:
        long_term.complete_topic(uid, body.topic, body.mastery or 1.0)
    elif body.type == "quiz_result" and body.topic:
        long_term.record_quiz_result(
            uid, body.topic, body.score or 0, body.total or 1, body.weak_concepts
        )
    elif body.type == "goal" and body.goal:
        long_term.add_goal(uid, body.goal)
    elif body.type == "preference" and body.preferences:
        long_term.set_preferences(uid, body.preferences)
    else:
        return {"ok": False, "reason": "unrecognized or incomplete event"}

    return {"ok": True, "profile": long_term.get_learner_profile(uid)}
