# LearnGraph — Interview & Portfolio Guide

A talking-track for discussing this project in software-engineering, AI-engineering,
and backend interviews. Each section is written so you can explain the *why*, not
just the *what*. Code references point at the real implementation.

---

## 1. System architecture

LearnGraph is a three-tier system:

- **Frontend** — Next.js (App Router) on Vercel. Handles auth UI, the streaming
  chat, the analytics dashboard, and resume upload. Talks to the backend over
  HTTPS + Server-Sent Events.
- **Backend** — FastAPI on Railway. Hosts the LangGraph agent runtime and the
  REST/SSE endpoints (`/chat/stream`, `/chat/resume`, `/auth/me`, `/progress/*`,
  `/resume/analyze`).
- **Data** — Supabase (Postgres + Auth). Stores users, learner profiles, topic
  progress, quiz results, roadmaps, and the LangGraph checkpoints.

The heart is a **LangGraph `StateGraph`** (`backend/app/agents/graph.py`):

```
load_memory → planner → supervisor → {specialist} → [ToolNode loop]
            → human_approval (high-impact) → memory_update → respond
```

Every request hydrates long-term memory, plans, is routed by a supervisor to a
specialist agent, optionally loops through tools (ReAct), optionally pauses for
human approval, persists durable facts, then responds — streamed token-by-token.

**One-paragraph version (for the "tell me about your project" prompt):**
> I built a multi-agent AI learning platform. Instead of a single prompt-response
> bot, a LangGraph supervisor routes each request to one of five specialist agents
> — tutor, quiz, roadmap, resume, interview — each a ReAct loop that can call
> tools. It has short-term memory via a Postgres checkpointer, long-term memory in
> Supabase, token streaming, human-in-the-loop approval for high-impact actions,
> CI/CD, tests, and rate-limited, secured APIs deployed on Railway and Vercel.

---

## 2. Why LangGraph

LangGraph models an agent as a **graph of nodes with explicit state and edges**,
rather than a hidden loop inside a framework. That mattered here because I needed:

- **Conditional routing** — a supervisor that picks a specialist (`add_conditional_edges`).
- **A real ReAct loop** — agent → `ToolNode` → back to agent, until no tool calls.
- **Durable state** — checkpointers persist state per `thread_id`, enabling
  conversation continuity and crash/interrupt recovery.
- **Human-in-the-loop** — first-class `interrupt()` that pauses the graph and
  resumes with `Command(resume=...)`.

A plain chain (e.g. LCEL) or a single ReAct `AgentExecutor` would have made
multi-agent routing, pause/resume, and per-user persistence awkward to build and
reason about. LangGraph makes the control flow explicit and testable (see
`tests/test_graph.py`, which drives the interrupt/resume cycle with a fake model).

---

## 3. Multi-agent design decisions

- **Supervisor pattern over a monolithic prompt.** A single mega-prompt with all
  ten tools is hard to steer and expensive. A supervisor classifies intent and
  delegates to a specialist whose system prompt and **tool subset** are scoped to
  its job (`TOOLS_BY_AGENT` in `backend/app/tools/__init__.py`).
- **Shared `ToolNode`.** All tools live in one node; specialists differ only in
  which tools they bind. This keeps the graph small and avoids duplicated tool
  wiring.
- **Planner before supervisor.** A short internal plan improves routing and gives
  the specialist a scaffold, without exposing the plan to the user (the streaming
  layer only emits specialist tokens — see §"streaming leak fix").
- **Stateless specialists, stateful graph.** Agents read/write the shared
  `AgentState`; durability is the graph's responsibility (checkpointer), not the
  agent's. This separation makes agents easy to test in isolation.

---

## 4. Human-in-the-loop workflow

High-impact routes (`roadmap`, `resume` — `HIGH_IMPACT_ROUTES` in
`backend/app/agents/nodes.py`) pause before their result is persisted:

1. The specialist produces its answer (streamed to the user).
2. The graph routes to `human_approval`, which calls `interrupt({...})`.
3. The run pauses; the checkpointer saves state. The SSE stream emits an
   `interrupt` event with the approval payload.
4. The UI shows **Approve / Reject**. The decision hits `/chat/resume`, which
   calls `graph.astream_events(Command(resume={"approved": bool}), ...)`.
5. Execution resumes *from the interrupt point*; `memory_update` persists the
   roadmap only when approved.

**Subtle bug I fixed:** `approved` is a checkpointed channel, so it persisted
across turns and the gate only fired once per thread. `load_memory` now resets it
each turn. I also namespaced `thread_id` by `user_id` so one user can't resume
another's paused run.

---

## 5. Memory architecture

| Type | Scope | Store | Code |
|---|---|---|---|
| Short-term | one conversation (`thread_id`) | LangGraph `PostgresSaver` | `memory/checkpointer.py` |
| Long-term | per user, durable | Supabase tables | `memory/long_term.py` |

- **Short-term** = the checkpointer. It snapshots graph state after every step,
  which is what makes recovery and HITL resume possible.
- **Long-term** = explicit domain tables (`learner_profiles`, `topic_progress`,
  `quiz_results`, `roadmaps`). `load_memory` injects a compact snapshot into the
  agent at run start; `memory_update` writes durable facts at the end.
- **Fallback:** when Supabase/DB aren't configured, both layers fall back to
  in-memory stores so the app (and the test suite) run with zero external
  dependencies.

Design choice: I kept long-term memory as **typed relational tables** rather than
dumping everything into a vector store, because the data is structured (scores,
XP, completion) and queried by exact user id. Semantic recall (embeddings) is a
documented future step in `SCALING.md`.

---

## 6. Security architecture

- **AuthN/Z:** Supabase issues JWTs; the backend verifies them (`api/deps.py`).
  Postgres **Row-Level Security** restricts rows to `auth.uid()`. The service-role
  key is backend-only.
- **Thread isolation:** `thread_id` is namespaced by `user_id` so conversation
  state can't be cross-accessed.
- **Rate limiting:** per-IP sliding window, with a tighter budget for expensive
  endpoints (`/chat`, `/resume`) — `security.py`.
- **Secure headers:** HSTS, CSP, X-Frame-Options, etc., on both API and frontend.
- **Input hardening:** Pydantic length caps, `Literal` value sets, thread-id
  charset, control-character stripping; PDF type + size limits.
- **Fail-safe errors:** a global handler returns sanitized messages (no stack
  traces); env validation fails fast in production if critical config is missing.

---

## 7. CI/CD architecture

Two GitHub Actions workflows (`.github/workflows/`):

- **Backend:** ruff lint + format check → mypy → pytest with a **70% coverage
  gate**.
- **Frontend:** eslint → `tsc --noEmit` → vitest → `next build`.

Both are **path-filtered** (backend changes don't trigger frontend CI) and run on
push and pull_request, so every PR is validated before merge. The coverage gate
makes "tests exist" enforceable, not aspirational.

---

## 8. Scalability discussion

See `SCALING.md` for the full story. Headlines:

- The graph runtime is **stateless per request**; horizontal scaling works as long
  as the **checkpointer is shared** (Postgres, not in-process memory).
- The current **rate limiter is in-process** — fine for one instance; move to
  Redis for multi-instance.
- LLM calls dominate latency; the path forward is a **queue + workers** (Celery/
  Redis or Kafka) for long-running agent jobs, plus streaming over websockets/SSE.
- Add a **vector DB** when semantic memory/retrieval is needed.

---

## 9. Tradeoffs made

- **Sync tool/LLM calls in nodes** (run in LangGraph's threadpool) instead of
  fully async — simpler code; acceptable because LLM latency dominates and nodes
  don't block the event loop. Would revisit under high concurrency.
- **Relational long-term memory** over vectors — right for structured progress
  data now; embeddings deferred until semantic recall is actually needed.
- **In-process rate limiting** over Redis — zero infra to start; documented
  upgrade path.
- **Built straight to LangGraph** rather than evolving from a bare chain — more
  upfront design, but the multi-agent/HITL requirements justified it.
- **Graceful tool fallbacks** (stubs when API keys absent) — keeps the system and
  tests runnable offline at the cost of "real" results without keys.

---

## 10. Future improvements

- Shared Redis for rate limiting + caching; websocket streaming.
- Celery/Kafka workers for long agent runs and background grading.
- Vector DB (pgvector / Pinecone) for semantic memory and RAG over notes.
- Quiz auto-grading wired back into `record_quiz_result` to close the analytics loop.
- Eval harness (LangSmith datasets) for regression-testing agent quality.
- Per-tenant model routing and cost controls; structured tool-output schemas.
- Frontend component tests with React Testing Library; E2E with Playwright.

---

## Resume bullets

**Short (one line):**
> Built a multi-agent AI learning platform (GPT-5, LangGraph, FastAPI, Next.js,
> Supabase) with tool-using agents, long-term memory, and streaming chat.

**Medium:**
> Designed and built a production-grade multi-agent AI tutor using LangGraph and
> GPT-5: a supervisor routes requests to five specialized ReAct agents backed by
> 10 tools, long-term Supabase memory, a Postgres checkpointer for stateful
> recovery, and token-streaming APIs — deployed on Railway/Vercel with CI/CD and a
> 70% test-coverage gate.

**Advanced:**
> Architected a multi-agent LLM platform on LangGraph featuring supervisor-based
> orchestration, ReAct tool-calling, human-in-the-loop approval via graph
> interrupts, and dual-layer memory (Postgres checkpointer + Supabase long-term
> store). Hardened for production with JWT auth, Postgres RLS, per-IP rate
> limiting, secure headers, input validation, and a model-agnostic config layer
> enabling one-line swaps between GPT-5, Claude, Gemini, and DeepSeek; shipped with
> GitHub Actions CI/CD, pytest/vitest suites, and Railway/Vercel deployment.
