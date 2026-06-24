"""Resume upload endpoint tests (PDF parsing + resume_review mocked)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_SAMPLE_TEXT = "Jane Doe\nSoftware Engineer\nBuilt scalable APIs in Python and managed Postgres."


def _mock_pipeline(monkeypatch, text=_SAMPLE_TEXT):
    monkeypatch.setattr("app.api.routes_resume.extract_text_from_pdf", lambda data: text)
    monkeypatch.setattr(
        "app.api.routes_resume.resume_review",
        type(
            "T",
            (),
            {
                "invoke": staticmethod(
                    lambda _: json.dumps({"ats_score": 78, "strengths": ["APIs"]})
                )
            },
        ),
    )


def test_analyze_resume_happy_path(monkeypatch):
    _mock_pipeline(monkeypatch)
    res = client.post(
        "/resume/analyze",
        files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
        data={"target_role": "Backend Engineer"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["target_role"] == "Backend Engineer"
    assert body["analysis"]["ats_score"] == 78
    assert body["characters_extracted"] > 0


def test_analyze_rejects_non_pdf(monkeypatch):
    _mock_pipeline(monkeypatch)
    res = client.post(
        "/resume/analyze",
        files={"file": ("resume.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 400


def test_analyze_rejects_unreadable_pdf(monkeypatch):
    _mock_pipeline(monkeypatch, text="short")  # below MIN_EXTRACTED_CHARS
    res = client.post(
        "/resume/analyze",
        files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert res.status_code == 422
