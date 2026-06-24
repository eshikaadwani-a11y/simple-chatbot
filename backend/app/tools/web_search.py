"""Web search tool (Tavily-backed with graceful fallback)."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from app.config import get_settings


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for up-to-date information on a topic.

    Use this when the user asks about current events, recent library versions,
    documentation, or anything that may be newer than the model's knowledge.
    Returns a JSON list of {title, url, snippet}.
    """
    settings = get_settings()
    if not settings.tavily_api_key:
        # Deterministic fallback so the agent still functions without a key.
        return json.dumps(
            {
                "note": "TAVILY_API_KEY not configured; returning no live results.",
                "query": query,
                "results": [],
            }
        )

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)
        resp = client.search(query=query, max_results=max_results, search_depth="advanced")
        results = [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "snippet": r.get("content", "")[:500],
            }
            for r in resp.get("results", [])
        ]
        return json.dumps({"query": query, "results": results})
    except Exception as exc:  # noqa: BLE001 - tools must never crash the graph
        return json.dumps({"query": query, "error": str(exc), "results": []})
