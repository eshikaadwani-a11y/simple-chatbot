# Knowledge-Aware Agent (RAG)

LearnGraph's Tutor and Interview agents are **grounded**: instead of answering DSA,
interview, system-design, and resume questions from the model's parametric memory
alone, they retrieve passages from a **curated knowledge base** and cite them. This
reduces hallucination and gives verifiable, source-attributed answers.

---

## Pipeline

```
User question
   │
   ▼
knowledge_search tool                (app/tools/knowledge_search.py)
   │
   ▼
Retriever  ──embed query──►  Embeddings   (OpenAI text-embedding-3-small, 1536-d)
   │                          (app/rag/embeddings.py)
   ▼
Vector store search          (app/rag/store.py)
   │   • pgvector via match_knowledge() RPC  (production)
   │   • in-memory cosine                    (dev/tests)
   ▼
Top-k passages + source attribution
   │
   ▼
GPT-5 specialist agent  ──►  Grounded, cited answer
```

The agent's system prompt instructs it to call `knowledge_search` **first** for
these topics and to **cite the returned sources** in its answer.

---

## Components

| Concern | File | Notes |
|---|---|---|
| Embeddings | `app/rag/embeddings.py` | OpenAI when `OPENAI_API_KEY` set; deterministic **hashing fallback** otherwise (keeps RAG working offline/in tests). Both 1536-dim. |
| Vector store | `app/rag/store.py` | `PgVectorStore` (Supabase RPC) or `InMemoryVectorStore` (cosine). Factory `get_vector_store()` picks based on config. |
| Retriever | `app/rag/retriever.py` | `retrieve(query, k)` → `[{source, title, snippet, score}]`. |
| Ingestion | `app/rag/ingest.py` | Chunks `app/knowledge/*.md` (≈800 chars, 120 overlap), embeds, writes to the store. Run: `python -m app.rag.ingest`. |
| Tool | `app/tools/knowledge_search.py` | LangChain tool the Tutor/Interview/General agents can call. |
| Knowledge base | `app/knowledge/*.md` | Seed content: DSA, interview prep, system design, resume guidance. |

---

## Storage schema (pgvector)

`supabase/schema.sql` creates:
- `knowledge_documents(id, source, title, chunk, embedding vector(1536), created_at)`
- an **IVFFlat** index on `embedding` for `vector_cosine_ops`
- a `match_knowledge(query_embedding, match_count)` SQL function returning the
  top matches with a cosine **score** (`1 - (embedding <=> query)`).

RLS is enabled with no public policy: retrieval flows through the backend
(service role), so the knowledge base isn't directly exposed to clients.

---

## Source attribution

Every retrieved passage carries its `source` (file) and `title`. The tool returns
them as JSON, and the agent is prompted to cite them — so answers can say
*"according to the DSA notes…"* and a user can trace the claim.

---

## Offline / dev behavior (graceful degradation)
- **No `OPENAI_API_KEY`** → deterministic hashing embeddings (lexical, not
  semantic, but stable) so retrieval still returns sensible lexical matches.
- **No Supabase** → in-memory store, auto-populated from the seed KB on first use.

This means the feature works in CI and local dev with zero setup, while production
uses real embeddings + pgvector. The quality difference is documented and expected.

---

## Extending the knowledge base
1. Add or edit markdown in `app/knowledge/`.
2. Re-run `python -m app.rag.ingest` (re-embeds and writes to the store).
3. For production, ensure `OPENAI_API_KEY` and Supabase/`DATABASE_URL` are set so
   real embeddings land in `knowledge_documents`.

> Future: ingest user-specific documents (e.g., their own notes) into a per-user
> namespace for personalized retrieval; add re-ranking and chunk-level dedup.

---

## Why this feature (depth over breadth)
RAG is the single highest-value addition because it demonstrates the **core skill
recruiters look for in AI engineers**: building a retrieval pipeline (embeddings →
vector search → grounding) with source attribution and a sensible
production/offline split — far more than adding another agent would.
