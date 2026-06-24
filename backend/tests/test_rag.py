"""RAG tests: embeddings, in-memory store, retriever, and the knowledge tool.

All offline — uses the deterministic hashing embeddings + in-memory store.
"""

from __future__ import annotations

import json

import pytest

from app.rag import store as store_mod
from app.rag.embeddings import EMBED_DIM, HashingEmbeddings
from app.rag.store import Doc, InMemoryVectorStore


@pytest.fixture(autouse=True)
def _reset_inmem_store():
    store_mod._INMEM_SINGLETON = None
    yield
    store_mod._INMEM_SINGLETON = None


def test_hashing_embeddings_deterministic_and_normalized():
    emb = HashingEmbeddings()
    v1 = emb.embed_query("binary search on a sorted array")
    v2 = emb.embed_query("binary search on a sorted array")
    assert v1 == v2
    assert len(v1) == EMBED_DIM
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_in_memory_store_ranks_by_similarity():
    emb = HashingEmbeddings()
    docs = [
        Doc(source="a.md", title="A", chunk="dynamic programming and memoization"),
        Doc(source="b.md", title="B", chunk="resume bullet points and ATS keywords"),
    ]
    for d in docs:
        d.embedding = emb.embed_query(d.chunk)
    store = InMemoryVectorStore()
    store.add(docs)

    hits = store.search(emb.embed_query("how does dynamic programming work"), k=2)
    assert hits[0][0].source == "a.md"  # most similar first
    assert hits[0][1] >= hits[1][1]


def test_retriever_returns_sources_offline():
    from app.rag.retriever import retrieve

    results = retrieve("binary search time complexity on a sorted array", k=3)
    assert len(results) >= 1
    top = results[0]
    assert {"source", "title", "snippet", "score"} <= set(top)
    # The DSA note should be the most relevant source for this query.
    assert any("dsa" in r["source"] for r in results)


def test_knowledge_search_tool_returns_json():
    from app.tools.knowledge_search import knowledge_search

    out = json.loads(knowledge_search.invoke({"query": "STAR method behavioral interview"}))
    assert out["query"]
    assert isinstance(out["results"], list)
    assert len(out["results"]) >= 1


def test_knowledge_search_registered_for_agents():
    from app.tools import TOOLS_BY_AGENT

    tutor_tools = {t.name for t in TOOLS_BY_AGENT["tutor"]}
    interview_tools = {t.name for t in TOOLS_BY_AGENT["interview"]}
    assert "knowledge_search" in tutor_tools
    assert "knowledge_search" in interview_tools
