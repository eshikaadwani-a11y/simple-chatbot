"""Tests for the JSON-extraction logic used by generative tools."""

from __future__ import annotations

from app.tools._llm_helper import _extract_json


def test_extract_plain_json():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_from_fenced_block():
    text = '```json\n{"a": 1, "b": [2, 3]}\n```'
    assert _extract_json(text) == {"a": 1, "b": [2, 3]}


def test_extract_json_with_surrounding_prose():
    text = 'Sure! Here you go: {"ok": true} hope that helps'
    assert _extract_json(text) == {"ok": True}


def test_extract_json_falls_back_to_raw_on_invalid():
    out = _extract_json("not json at all")
    assert out == {"raw": "not json at all"}
