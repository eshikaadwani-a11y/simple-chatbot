# Scaling LearnGraph

How the system scales today, where it breaks first, and the staged path to a
distributed architecture. Written to support a system-design conversation.

---

## Current architecture

```
Browser ──HTTPS/SSE──► FastAPI (1+ instances, Railway)
                          │
                          ├── LangGraph runtime (stateless per request)
                          ├── LLM calls (OpenAI GPT-5)  ← latency dominator
                          └── Supabase / Postgres
                                ├── auth + RLS
                                ├── long-term memory tables
                                └── LangGraph checkpoints (short-term memory)
```

**Properties today**
- The agent runtime holds **no per-request state in process** — durable state
  lives in the checkpointer. So multiple FastAPI instances can serve the same user
  *as long as the checkpointer is the shared Postgres one* (`DATABASE_URL` set),
  not the in-memory fallback.
- Streaming uses SSE; each in-flight chat holds one worker coroutine while the LLM
  streams.

**First bottlenecks**
1. **In-process rate limiter** (`security.py`) — counters aren't shared across
   instances. Multi-instance ⇒ move to Redis.
2. **In-memory checkpointer** if `DATABASE_URL` is unset — breaks HITL resume
   across workers. Always use Postgres in production.
3. **Synchronous LLM/tool calls** run in a threadpool; many concurrent long runs
   exhaust workers.
4. **LLM latency/cost** is the dominant constraint, not CPU.

---

## Future architecture (staged)

### Stage 1 — Single agent (origin)
One model, one prompt, request/response. Simple, but no routing, memory, or
resumability. (Where most "chatbots" stop.)

### Stage 2 — Multi-agent (where LearnGraph is now)
Supervisor + specialist agents, shared tools, dual-layer memory, HITL. Scales
horizontally behind a load balancer with a shared Postgres checkpointer.

```
LB ─► FastAPI×N ─► LangGraph ─► Postgres (checkpoints + memory)
                         └─► GPT-5
```

### Stage 3 — Queue system
Move long-running agent jobs off the request path. The API enqueues a job and
streams results as they're produced; workers run the graph.

```
API ──► Redis queue ──► Celery workers (run LangGraph) ──► Postgres
   └── Redis: rate limits, response/tool caching, pub/sub for streaming
```

- **Redis**: distributed rate limiting, caching (tool results, embeddings),
  and pub/sub to fan streamed tokens back to the right client.
- **Celery**: background execution of agent runs, quiz grading, resume parsing;
  retries and scheduling (e.g. spaced-repetition reminders).

### Stage 4 — Distributed workers + event streaming
At higher volume, replace point-to-point queues with an event log.

```
API ─► Kafka (topics: agent.requests, agent.events, progress.events)
        ├─► Agent workers (consumer group, autoscaled)
        ├─► Analytics consumers (materialize dashboards)
        └─► Memory writers
```

- **Kafka**: durable, replayable event backbone; decouples producers/consumers;
  enables analytics pipelines and audit trails. Choose over Celery/Redis when you
  need high throughput, replay, and multiple independent consumers.
- **Kubernetes**: run FastAPI and worker pools as separately autoscaled
  deployments (HPA on queue depth / CPU), rolling deploys, secrets, and config
  maps. Railway is great early; K8s (EKS/GKE) is the destination at scale.

### Stage 5 — Semantic memory
Add a **vector database** for retrieval-augmented memory and recommendations.

- **pgvector** first (stay on Postgres/Supabase — one fewer system) for embeddings
  of notes, completed topics, and learner history.
- **Pinecone / Weaviate / Qdrant** if vector workloads outgrow Postgres (billions
  of vectors, advanced filtering, managed scaling).
- Use it for: semantic recall of past learning, RAG over generated notes, and
  "students like you also studied…" recommendations.

---

## Capacity & cost levers

- **Streaming concurrency:** bound in-flight LLM streams per instance; shed load
  with the rate limiter / queue depth.
- **Caching:** cache deterministic tool outputs (search, YouTube) and embeddings
  in Redis to cut LLM/tool calls.
- **Model tiering:** route cheap/short tasks to a smaller model (`gpt-5-mini`) via
  the existing model registry; reserve the flagship for hard reasoning.
- **Backpressure:** queue + worker pool smooths spikes and protects the DB and the
  upstream LLM provider's rate limits.

---

## Summary table

| Concern | Today | Next step |
|---|---|---|
| Rate limiting | in-process | Redis |
| Short-term memory | Postgres checkpointer | (unchanged) — already shareable |
| Long-running jobs | inline (threadpool) | Celery/Redis → Kafka |
| Token streaming | SSE per worker | Redis pub/sub + websockets |
| Semantic recall | none | pgvector → dedicated vector DB |
| Orchestration | FastAPI + workers on Railway | Kubernetes (autoscaled pools) |
