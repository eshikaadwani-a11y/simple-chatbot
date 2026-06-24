"""Knowledge-base search tool (RAG retrieval with source attribution)."""

from __future__ import annotations

import json

from langchain_core.tools import tool


@tool
def knowledge_search(query: str, k: int = 4) -> str:
    """Search LearnGraph's curated knowledge base for grounded, cited answers.

    The knowledge base covers DSA, technical-interview prep, system design, and
    resume guidance. Prefer this over a general web search for these foundational
    topics, and **cite the returned sources** in your answer.

    Returns JSON: {query, results:[{source, title, snippet, score}]}.
    """
    from app.rag.retriever import retrieve

    try:
        results = retrieve(query, k)
        return json.dumps({"query": query, "results": results})
    except Exception as exc:  # noqa: BLE001 - tools must never crash the graph
        return json.dumps({"query": query, "results": [], "error": str(exc)})
