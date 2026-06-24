"""Model registry / config-driven selection tests (no network)."""

from __future__ import annotations

import pytest

from app.agents import models


def test_registry_lists_expected_models():
    names = models.list_models()
    assert "gpt-5" in names
    # Alternate providers are configured for easy swapping.
    for alt in ("claude", "gemini", "deepseek"):
        assert alt in names


def test_default_model_name_prefers_env(monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("LEARNGRAPH_DEFAULT_MODEL", "claude")
    get_settings.cache_clear()
    assert models.default_model_name() == "claude"
    get_settings.cache_clear()


def test_unknown_model_raises():
    with pytest.raises(KeyError):
        models.get_chat_model("does-not-exist")
