"""Vector store abstraction with two backends.

- ``PgVectorStore``  — Supabase/pgvector via a ``match_knowledge`` RPC (production).
- ``InMemoryVectorStore`` — cosine similarity over an in-process list (dev/tests),
  auto-populated from the seed knowledge base on first use.

``get_vector_store()`` picks pgvector when Supabase is configured, else in-memory.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from app.db.supabase_client import get_supabase

logger = logging.getLogger("learngraph")


@dataclass
class Doc:
    source: str
    title: str
    chunk: str
    embedding: list[float] = field(default_factory=list)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._docs: list[Doc] = []

    def add(self, docs: list[Doc]) -> None:
        self._docs.extend(docs)

    def search(self, query_vec: list[float], k: int) -> list[tuple[Doc, float]]:
        scored = [(d, _cosine(query_vec, d.embedding)) for d in self._docs]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def count(self) -> int:
        return len(self._docs)


class PgVectorStore:
    def __init__(self, sb) -> None:  # noqa: ANN001
        self._sb = sb

    def add(self, docs: list[Doc]) -> None:
        rows = [
            {"source": d.source, "title": d.title, "chunk": d.chunk, "embedding": d.embedding}
            for d in docs
        ]
        # Insert in batches to stay under request size limits.
        for i in range(0, len(rows), 100):
            self._sb.table("knowledge_documents").insert(rows[i : i + 100]).execute()

    def search(self, query_vec: list[float], k: int) -> list[tuple[Doc, float]]:
        res = self._sb.rpc(
            "match_knowledge", {"query_embedding": query_vec, "match_count": k}
        ).execute()
        out: list[tuple[Doc, float]] = []
        for row in res.data or []:
            out.append(
                (
                    Doc(
                        source=row.get("source", ""),
                        title=row.get("title", ""),
                        chunk=row.get("chunk", ""),
                    ),
                    float(row.get("score", 0.0)),
                )
            )
        return out

    def count(self) -> int:
        try:
            return (
                self._sb.table("knowledge_documents").select("id", count="exact").execute().count
                or 0
            )
        except Exception:  # noqa: BLE001
            return 0


_INMEM_SINGLETON: InMemoryVectorStore | None = None


def get_vector_store():
    """Return the active vector store (pgvector if Supabase configured, else in-memory).

    The in-memory store is auto-populated from the seed knowledge base the first
    time it is created so retrieval works with zero setup in dev/tests.
    """
    sb = get_supabase()
    if sb is not None:
        return PgVectorStore(sb)

    global _INMEM_SINGLETON
    if _INMEM_SINGLETON is None:
        _INMEM_SINGLETON = InMemoryVectorStore()
        try:
            from app.rag.ingest import populate_store

            populate_store(_INMEM_SINGLETON)
            logger.info("In-memory knowledge base loaded: %d chunks.", _INMEM_SINGLETON.count())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Seed KB load failed: %s", exc)
    return _INMEM_SINGLETON
