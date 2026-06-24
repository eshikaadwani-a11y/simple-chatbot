"""Retrieval-Augmented Generation (RAG) — knowledge-aware retrieval.

Pipeline: query -> embed -> vector search (pgvector or in-memory) -> top-k
passages with source attribution -> grounded answer by the agent.
"""
