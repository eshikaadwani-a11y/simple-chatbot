"""Long-term memory & analytics tests (in-memory fallback)."""

from __future__ import annotations

import datetime as dt

from app.memory import long_term


def test_default_profile_created():
    profile = long_term.get_learner_profile("u1")
    assert profile["user_id"] == "u1"
    assert profile["xp"] == 0
    assert profile["goals"] == []


def test_award_xp_accumulates_and_starts_streak():
    long_term.award_xp("u1", 10)
    p = long_term.award_xp("u1", 5)
    assert p["xp"] == 15
    assert p["streak_days"] == 1


def test_streak_increments_on_consecutive_day(monkeypatch):
    long_term.award_xp("u1", 10)  # establishes last_active = today, streak 1
    # Simulate that the last activity was yesterday.
    yesterday = (dt.datetime.now(dt.UTC).date() - dt.timedelta(days=1)).isoformat()
    long_term.update_learner_profile("u1", {"last_active": yesterday, "streak_days": 1})
    p = long_term.award_xp("u1", 10)
    assert p["streak_days"] == 2


def test_streak_resets_after_gap():
    long_term.award_xp("u1", 10)
    old = (dt.datetime.now(dt.UTC).date() - dt.timedelta(days=5)).isoformat()
    long_term.update_learner_profile("u1", {"last_active": old, "streak_days": 9})
    p = long_term.award_xp("u1", 10)
    assert p["streak_days"] == 1


def test_add_goal_dedupes():
    long_term.add_goal("u1", "Learn backend")
    long_term.add_goal("u1", "Learn backend")
    long_term.add_goal("u1", "Learn DSA")
    goals = long_term.get_learner_profile("u1")["goals"]
    assert goals == ["Learn backend", "Learn DSA"]


def test_set_preferences_merges():
    long_term.set_preferences("u1", {"tone": "concise"})
    long_term.set_preferences("u1", {"format": "bullets"})
    prefs = long_term.get_learner_profile("u1")["preferences"]
    assert prefs == {"tone": "concise", "format": "bullets"}


def test_complete_topic_records_and_awards_xp():
    long_term.complete_topic("u1", "Big-O", 0.9)
    topics = long_term.get_topic_progress("u1")
    assert len(topics) == 1 and topics[0]["topic"] == "Big-O"
    assert long_term.get_learner_profile("u1")["xp"] >= 25


def test_quiz_result_and_weak_area_detection():
    long_term.record_quiz_result("u1", "Trees", score=2, total=5, weak_concepts=["BST", "AVL"])
    long_term.record_quiz_result("u1", "Trees", score=1, total=5, weak_concepts=["BST"])
    analytics = long_term.compute_analytics("u1")
    assert analytics["quizzes_taken"] == 2
    # BST appears in two low-scoring quizzes -> should rank first.
    assert analytics["weak_areas"][0] == "BST"
    assert analytics["average_quiz_score"] is not None


def test_save_and_get_roadmap():
    long_term.save_roadmap("u1", "Become a backend engineer", {"milestones": []})
    roadmaps = long_term.get_roadmaps("u1")
    assert len(roadmaps) == 1
    assert roadmaps[0]["goal"] == "Become a backend engineer"


def test_compute_analytics_focus_variants():
    long_term.complete_topic("u1", "Hashing", 0.8)
    assert "mastery" in long_term.compute_analytics("u1", focus="mastery")
    assert "streak_days" in long_term.compute_analytics("u1", focus="streak")
    assert "weak_areas" in long_term.compute_analytics("u1", focus="weak_areas")


def test_load_memory_context_shape():
    long_term.add_goal("u1", "Learn SQL")
    long_term.complete_topic("u1", "Joins", 1.0)
    ctx = long_term.load_memory_context("u1")
    assert ctx["goals"] == ["Learn SQL"]
    assert "Joins" in ctx["completed_topics"]
