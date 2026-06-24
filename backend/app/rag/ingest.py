"""Ingest the seed knowledge base into the active vector store.

Run as a one-off after deploy:  ``python -m app.rag.ingest``

Reads markdown from ``app/knowledge/``, splits into overlapping chunks, embeds
them, and writes them to the vector store (pgvector in prod, in-memory in dev).
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.rag.embeddings import get_embeddings
from app.rag.store import Doc

logger = logging.getLogger("learngraph")

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


def _chunk(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]


def load_seed_chunks() -> list[Doc]:
    """Load and chunk all markdown in the knowledge dir (without embeddings)."""
    docs: list[Doc] = []
    if not _KNOWLEDGE_DIR.exists():
        return docs
    for path in sorted(_KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip() if text else path.stem
        for chunk in _chunk(text):
            docs.append(Doc(source=path.name, title=title, chunk=chunk))
    return docs


def populate_store(store) -> int:  # noqa: ANN001
    """Embed the seed knowledge and add it to ``store``. Returns chunk count."""
    embeddings = get_embeddings()
    docs = load_seed_chunks()
    if not docs:
        return 0
    vectors = embeddings.embed_documents([d.chunk for d in docs])
    for doc, vec in zip(docs, vectors, strict=False):
        doc.embedding = vec
    store.add(docs)
    return len(docs)


def ingest() -> int:
    """Populate the production/active vector store. Returns chunk count."""
    from app.rag.store import get_vector_store

    count = populate_store(get_vector_store())
    logger.info("Ingested %d knowledge chunks.", count)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Ingested {ingest()} knowledge chunks.")
