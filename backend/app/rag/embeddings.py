"""Embeddings for RAG.

Uses OpenAI ``text-embedding-3-small`` (1536-dim) when an API key is configured;
otherwise falls back to a deterministic hashing embedding so retrieval still works
offline and in tests (no network). Both produce 1536-dim vectors so the pgvector
schema and the in-memory store are interchangeable.
"""

from __future__ import annotations

import functools
import hashlib
import math
import re

from app.config import get_settings

EMBED_DIM = 1536
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class HashingEmbeddings:
    """Deterministic offline embedding (hashed bag-of-words, L2-normalized).

    Not semantically rich like a trained model, but stable and comparable — enough
    for the feature to function without an API key. Production uses OpenAI.
    """

    dimension = EMBED_DIM

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        for tok in _tokenize(text):
            idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % self.dimension
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]


@functools.lru_cache
def get_embeddings():
    """Return an embeddings client (OpenAI if configured, else hashing fallback)."""
    settings = get_settings()
    if settings.openai_api_key:
        try:
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(model=settings.embedding_model)
        except Exception:  # noqa: BLE001 - fall back rather than crash
            pass
    return HashingEmbeddings()
