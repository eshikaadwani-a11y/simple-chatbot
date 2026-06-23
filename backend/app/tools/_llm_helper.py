"""Shared helper for LLM-generative tools.

Several tools (roadmap, quiz, notes, resume, interview, dsa) produce structured
content with the LLM. They share this thin wrapper so prompt/JSON handling is
consistent and robust to occasional non-JSON output.
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.models import get_chat_model


def generate_json(system_prompt: str, user_prompt: str, *, model: str | None = None) -> dict[str, Any]:
    """Invoke the configured LLM and parse a JSON object from the response."""
    llm = get_chat_model(model)
    messages = [
        SystemMessage(content=system_prompt + "\n\nRespond ONLY with valid minified JSON."),
        HumanMessage(content=user_prompt),
    ]
    resp = llm.invoke(messages)
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    return _extract_json(text)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("\n") + 1 :] if "\n" in text else text
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {"raw": text}
