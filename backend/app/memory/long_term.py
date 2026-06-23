"""Long-term memory — durable, per-user learner state in Supabase/Postgres.

Stores and retrieves:
  * learner profile (goals, preferences, XP, streak)
  * topic progress (completed topics, mastery)
  * quiz results (scores, weak concepts)
  * roadmaps (generated plans + progress)

If Supabase is not configured, an in-memory fallback keeps the app runnable for
local development and tests.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any

from app.db.supabase_client import get_supabase

# ----------------------------------------------------------------------------
# In-memory fallback store (used only when Supabase is not configured)
# ----------------------------------------------------------------------------
_MEM: dict[str, dict[str, Any]] = defaultdict(
    lambda: {"profile": {}, "topics": [], "quizzes": [], "roadmaps": []}
)


def _today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


# ----------------------------------------------------------------------------
# Profile
# ----------------------------------------------------------------------------
def get_learner_profile(user_id: str) -> dict[str, Any]:
    """Return the learner profile, creating a default if none exists."""
    sb = get_supabase()
    if sb is None:
        return _MEM[user_id]["profile"] or _default_profile(user_id)

    res = sb.table("learner_profiles").select("*").eq("user_id", user_id).limit(1).execute()
    rows = res.data or []
    if rows:
        return rows[0]
    profile = _default_profile(user_id)
    sb.table("learner_profiles").insert(profile).execute()
    return profile


def _default_profile(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "goals": [],
        "preferences": {},
        "xp": 0,
        "streak_days": 0,
        "last_active": None,
    }


def update_learner_profile(user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    sb = get_supabase()
    if sb is None:
        _MEM[user_id]["profile"] = {**get_learner_profile(user_id), **patch}
        return _MEM[user_id]["profile"]
    sb.table("learner_profiles").update(patch).eq("user_id", user_id).execute()
    return get_learner_profile(user_id)


def add_goal(user_id: str, goal: str) -> None:
    profile = get_learner_profile(user_id)
    goals = list(profile.get("goals") or [])
    if goal and goal not in goals:
        goals.append(goal)
        update_learner_profile(user_id, {"goals": goals})


def set_preferences(user_id: str, preferences: dict[str, Any]) -> None:
    profile = get_learner_profile(user_id)
    merged = {**(profile.get("preferences") or {}), **preferences}
    update_learner_profile(user_id, {"preferences": merged})


# ----------------------------------------------------------------------------
# XP + streak
# ----------------------------------------------------------------------------
def award_xp(user_id: str, amount: int) -> dict[str, Any]:
    """Award XP and update the daily streak. Returns the updated profile."""
    profile = get_learner_profile(user_id)
    xp = int(profile.get("xp") or 0) + max(0, amount)

    last_active = profile.get("last_active")
    streak = int(profile.get("streak_days") or 0)
    today = _today()
    if last_active:
        try:
            last = dt.date.fromisoformat(str(last_active)[:10])
        except ValueError:
            last = None
        if last == today:
            pass  # already counted today
        elif last == today - dt.timedelta(days=1):
            streak += 1
        else:
            streak = 1
    else:
        streak = 1

    return update_learner_profile(
        user_id,
        {"xp": xp, "streak_days": streak, "last_active": today.isoformat()},
    )


# ----------------------------------------------------------------------------
# Topic progress
# ----------------------------------------------------------------------------
def complete_topic(user_id: str, topic: str, mastery: float = 1.0) -> None:
    sb = get_supabase()
    row = {
        "user_id": user_id,
        "topic": topic,
        "mastery": mastery,
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    if sb is None:
        _MEM[user_id]["topics"].append(row)
    else:
        sb.table("topic_progress").upsert(row, on_conflict="user_id,topic").execute()
    award_xp(user_id, 25)


def get_topic_progress(user_id: str) -> list[dict[str, Any]]:
    sb = get_supabase()
    if sb is None:
        return _MEM[user_id]["topics"]
    res = sb.table("topic_progress").select("*").eq("user_id", user_id).execute()
    return res.data or []


# ----------------------------------------------------------------------------
# Quiz results
# ----------------------------------------------------------------------------
def record_quiz_result(
    user_id: str, topic: str, score: float, total: int, weak_concepts: list[str] | None = None
) -> None:
    sb = get_supabase()
    row = {
        "user_id": user_id,
        "topic": topic,
        "score": score,
        "total": total,
        "weak_concepts": weak_concepts or [],
        "taken_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    if sb is None:
        _MEM[user_id]["quizzes"].append(row)
    else:
        sb.table("quiz_results").insert(row).execute()
    award_xp(user_id, int(round(10 * (score / total))) if total else 5)


def get_quiz_results(user_id: str) -> list[dict[str, Any]]:
    sb = get_supabase()
    if sb is None:
        return _MEM[user_id]["quizzes"]
    res = sb.table("quiz_results").select("*").eq("user_id", user_id).execute()
    return res.data or []


# ----------------------------------------------------------------------------
# Roadmaps
# ----------------------------------------------------------------------------
def save_roadmap(user_id: str, goal: str, plan: dict[str, Any]) -> None:
    sb = get_supabase()
    row = {
        "user_id": user_id,
        "goal": goal,
        "plan": plan,
        "progress": 0,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    if sb is None:
        _MEM[user_id]["roadmaps"].append(row)
    else:
        sb.table("roadmaps").insert(row).execute()


def get_roadmaps(user_id: str) -> list[dict[str, Any]]:
    sb = get_supabase()
    if sb is None:
        return _MEM[user_id]["roadmaps"]
    res = sb.table("roadmaps").select("*").eq("user_id", user_id).execute()
    return res.data or []


# ----------------------------------------------------------------------------
# Aggregations
# ----------------------------------------------------------------------------
def load_memory_context(user_id: str) -> dict[str, Any]:
    """Compact long-term memory snapshot injected into the agent at run start."""
    profile = get_learner_profile(user_id)
    topics = get_topic_progress(user_id)
    return {
        "goals": profile.get("goals") or [],
        "preferences": profile.get("preferences") or {},
        "xp": profile.get("xp") or 0,
        "streak_days": profile.get("streak_days") or 0,
        "completed_topics": [t["topic"] for t in topics],
    }


def compute_analytics(user_id: str, focus: str = "overview") -> dict[str, Any]:
    """Compute XP, streak, mastery, and weak areas from stored data."""
    profile = get_learner_profile(user_id)
    topics = get_topic_progress(user_id)
    quizzes = get_quiz_results(user_id)

    # Weak-area detection: concepts that recur in low-scoring quizzes.
    weak_counter: dict[str, int] = defaultdict(int)
    for q in quizzes:
        ratio = (q.get("score") or 0) / (q.get("total") or 1)
        if ratio < 0.7:
            for c in q.get("weak_concepts") or []:
                weak_counter[c] += 1
    weak_areas = sorted(weak_counter, key=weak_counter.get, reverse=True)[:5]

    avg_score = (
        round(sum((q.get("score") or 0) / (q.get("total") or 1) for q in quizzes) / len(quizzes), 3)
        if quizzes
        else None
    )

    overview = {
        "user_id": user_id,
        "xp": profile.get("xp") or 0,
        "streak_days": profile.get("streak_days") or 0,
        "topics_completed": len(topics),
        "quizzes_taken": len(quizzes),
        "average_quiz_score": avg_score,
        "weak_areas": weak_areas,
        "goals": profile.get("goals") or [],
    }

    if focus == "weak_areas":
        return {"weak_areas": weak_areas, "detail": dict(weak_counter)}
    if focus == "streak":
        return {"streak_days": overview["streak_days"], "last_active": profile.get("last_active")}
    if focus == "mastery":
        return {"mastery": [{"topic": t["topic"], "mastery": t.get("mastery")} for t in topics]}
    return overview
