"""Tool execution tests. LLM-backed tools have their generator mocked."""

from __future__ import annotations

import json

from app.tools import ALL_TOOLS, TOOLS_BY_AGENT
from app.tools.dsa_mentor import dsa_mentor
from app.tools.interview import interview_prep
from app.tools.notes import notes_generator
from app.tools.quiz import quiz_generator
from app.tools.resources import resource_recommender
from app.tools.resume_review import resume_review
from app.tools.roadmap import roadmap_generator
from app.tools.web_search import web_search
from app.tools.youtube import youtube_learning


def test_registry_maps_agents_to_tools():
    assert set(TOOLS_BY_AGENT) == {
        "tutor",
        "quiz",
        "roadmap",
        "resume",
        "interview",
        "general",
    }
    # ALL_TOOLS is the de-duplicated union.
    names = {t.name for t in ALL_TOOLS}
    assert "quiz_generator" in names
    assert "roadmap_generator" in names
    assert len(names) == len(ALL_TOOLS)  # no duplicates


def test_web_search_without_key_returns_stub():
    out = json.loads(web_search.invoke({"query": "langgraph tutorial"}))
    assert out["results"] == []
    assert "query" in out


def test_youtube_without_key_returns_search_link():
    out = json.loads(youtube_learning.invoke({"topic": "binary search"}))
    assert "search_url" in out
    assert out["results"] == []


def test_roadmap_generator_uses_llm(monkeypatch):
    monkeypatch.setattr(
        "app.tools.roadmap.generate_json",
        lambda *a, **k: {"milestones": [{"week": 1, "title": "Basics"}]},
    )
    out = json.loads(roadmap_generator.invoke({"goal": "Backend", "weeks": 4}))
    assert out["goal"] == "Backend"
    assert out["weeks"] == 4
    assert out["milestones"][0]["title"] == "Basics"


def test_quiz_generator_uses_llm(monkeypatch):
    monkeypatch.setattr(
        "app.tools.quiz.generate_json",
        lambda *a, **k: {"questions": [{"id": 1, "type": "mcq"}]},
    )
    out = json.loads(quiz_generator.invoke({"topic": "Graphs", "num_questions": 3}))
    assert out["topic"] == "Graphs"
    assert out["questions"][0]["type"] == "mcq"


def test_notes_generator_uses_llm(monkeypatch):
    monkeypatch.setattr(
        "app.tools.notes.generate_json", lambda *a, **k: {"sections": [{"heading": "Intro"}]}
    )
    out = json.loads(notes_generator.invoke({"topic": "REST"}))
    assert out["topic"] == "REST"


def test_resume_review_uses_llm(monkeypatch):
    monkeypatch.setattr("app.tools.resume_review.generate_json", lambda *a, **k: {"ats_score": 82})
    out = json.loads(resume_review.invoke({"resume_text": "x", "target_role": "SWE"}))
    assert out["ats_score"] == 82
    assert out["target_role"] == "SWE"


def test_interview_prep_uses_llm(monkeypatch):
    monkeypatch.setattr("app.tools.interview.generate_json", lambda *a, **k: {"questions": []})
    out = json.loads(interview_prep.invoke({"role": "Backend", "interview_type": "technical"}))
    assert out["role"] == "Backend"
    assert out["type"] == "technical"


def test_dsa_mentor_uses_llm(monkeypatch):
    monkeypatch.setattr(
        "app.tools.dsa_mentor.generate_json", lambda *a, **k: {"approach": "two pointers"}
    )
    out = json.loads(dsa_mentor.invoke({"topic_or_problem": "two sum", "mode": "hints"}))
    assert out["mode"] == "hints"


def test_resource_recommender_uses_llm(monkeypatch):
    monkeypatch.setattr("app.tools.resources.generate_json", lambda *a, **k: {"books": []})
    out = json.loads(resource_recommender.invoke({"topic": "SQL", "level": "beginner"}))
    assert out["topic"] == "SQL"
