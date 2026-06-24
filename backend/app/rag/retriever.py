"""Retrieval entry point: embed a query and return top-k passages with sources."""

from __future__ import annotations

from typing import Any

from app.rag.embeddings import get_embeddings
from app.rag.store import get_vector_store


def retrieve(query: str, k: int = 4) -> list[dict[str, Any]]:
    """Return the top-k knowledge passages for ``query`` with source attribution.

    Each result: ``{source, title, snippet, score}`` sorted by relevance.
    """
    embeddings = get_embeddings()
    store = get_vector_store()
    query_vec = embeddings.embed_query(query)
    hits = store.search(query_vec, k)
    return [
        {
            "source": doc.source,
            "title": doc.title,
            "snippet": doc.chunk[:600],
            "score": round(float(score), 4),
        }
        for doc, score in hits
    ]
