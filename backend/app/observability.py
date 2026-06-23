"""LangSmith observability wiring.

Calling ``configure_observability()`` at startup sets the environment variables
LangChain/LangGraph read to emit traces to LangSmith. Tracing is opt-in via
``LANGCHAIN_TRACING_V2`` so the app runs fine with no observability configured.
"""
from __future__ import annotations

import logging
import os

from app.config import get_settings

logger = logging.getLogger("learngraph")


def configure_observability() -> None:
    settings = get_settings()
    if not settings.langchain_tracing_v2 or not settings.langchain_api_key:
        logger.info("LangSmith tracing disabled.")
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
    logger.info("LangSmith tracing enabled for project '%s'.", settings.langchain_project)
