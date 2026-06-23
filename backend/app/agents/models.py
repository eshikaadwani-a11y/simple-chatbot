"""Config-driven LLM factory.

The agent never hard-codes a model. Instead it asks this factory for a chat
model by logical name (e.g. "gpt-5"). The mapping from name -> provider/model/
params lives in ``models.yaml``. Swapping GPT-5 for Claude, Gemini, or DeepSeek
is therefore a one-line config change with zero code edits.

Under the hood we use LangChain's ``init_chat_model`` which returns a provider-
agnostic ``BaseChatModel`` supporting ``.bind_tools`` and streaming.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import get_settings

_REGISTRY_PATH = Path(__file__).with_name("models.yaml")


@functools.lru_cache
def _load_registry() -> dict[str, Any]:
    with _REGISTRY_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "models" not in data:
        raise ValueError("models.yaml must define a top-level 'models' mapping")
    return data


def list_models() -> list[str]:
    """Return the names of all configured models (for diagnostics / UI)."""
    return list(_load_registry()["models"].keys())


def default_model_name() -> str:
    """Default model: env override wins, else the registry default."""
    settings = get_settings()
    if settings.learngraph_default_model:
        return settings.learngraph_default_model
    return _load_registry().get("default", "gpt-5")


@functools.lru_cache(maxsize=16)
def get_chat_model(name: str | None = None, *, streaming: bool = False) -> BaseChatModel:
    """Return a ready-to-use chat model for the given logical name.

    Args:
        name: a key from models.yaml (e.g. "gpt-5", "claude"). Defaults to the
            configured default model.
        streaming: enable token streaming.
    """
    # Imported lazily so the module imports cleanly even before deps install.
    from langchain.chat_models import init_chat_model

    registry = _load_registry()
    name = name or default_model_name()

    entry = registry["models"].get(name)
    if entry is None:
        raise KeyError(
            f"Unknown model '{name}'. Configured models: {list_models()}"
        )

    provider = entry["provider"]
    model = entry["model"]
    params = dict(entry.get("params") or {})
    if streaming:
        params["streaming"] = True

    return init_chat_model(model=model, model_provider=provider, **params)
