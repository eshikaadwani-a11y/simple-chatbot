# Architecture Decision Records (ADRs)

Each decision lists the **context**, the **choice**, **alternatives considered**,
and the **tradeoffs**. These are the questions recruiters and engineers most often
probe, so the reasoning matters as much as the pick.

---

## ADR-001 — Model: GPT-5 (with a model-agnostic abstraction)

**Context.** The agents need strong reasoning and reliable tool-calling (the ReAct
loop depends on well-formed tool calls).

**Decision.** Use **GPT-5** as the default model, but never hard-code it. A config
registry (`backend/app/agents/models.yaml`) maps logical names to provider/model,
resolved at runtime via LangChain's `init_chat_model`.

**Alternatives.** Hard-coding one provider's SDK; building per-provider adapters by
hand.

**Tradeoffs.** GPT-5 is a paid, external dependency and a cost/latency driver. The
abstraction adds a small indirection layer but buys **one-line model swaps**
(Claude/Gemini/DeepSeek/local), easy A/B testing, and no vendor lock-in. Worth it.

---

## ADR-002 — Orchestration: LangGraph

**Context.** Requirements include multi-agent routing, a tool loop, durable state,
and human-in-the-loop — i.e. **explicit, resumable control flow**.

**Decision.** Use **LangGraph `StateGraph`** with conditional edges, a shared
`ToolNode`, a checkpointer, and `interrupt()`/`Command(resume=...)`.

**Alternatives.** LCEL chains; a single `AgentExecutor`; a hand-rolled state
machine; CrewAI/AutoGen.

**Tradeoffs.** LangGraph has a learning curve and is younger than plain LangChain
chains. But it makes routing, the ReAct loop, persistence, and pause/resume
**first-class and testable**, which a chain or bespoke loop would not. The
multi-agent + HITL requirements justified the upfront design cost.

---

## ADR-003 — Backend: FastAPI

**Context.** Need async I/O, **streaming** (SSE) for token output, dependency
injection for auth, and automatic validation/docs.

**Decision.** **FastAPI** + Uvicorn, with `sse-starlette` for streaming.

**Alternatives.** Flask (sync-first, weaker streaming ergonomics); Django (heavy
for an API); Node/Express (would split the stack across languages).

**Tradeoffs.** FastAPI's Pydantic-everywhere style adds boilerplate, and true async
benefits require async-aware libraries (we run sync LLM/tool calls in a threadpool).
In exchange we get native async, clean SSE, typed request validation, DI for the
JWT dependency, and OpenAPI docs for free.

---

## ADR-004 — Auth + Database: Supabase

**Context.** Need authentication (signup/login, JWT), a relational store for
structured learner data, and row-level security — without building an auth service.

**Decision.** **Supabase** (managed Postgres + Auth). JWTs verified on the backend;
**RLS** scopes rows to `auth.uid()`; a trigger auto-provisions a profile on signup.

**Alternatives.** Roll-your-own auth + raw Postgres; Firebase (NoSQL, less suited
to relational progress data); Auth0 + separate DB (two vendors).

**Tradeoffs.** Supabase is another managed dependency and its client is sync. But
it collapses auth + Postgres + RLS into one platform with a generous free tier,
and Postgres is the right model for the structured, relational data here. It also
hosts the LangGraph checkpoint tables, keeping state in one place.

---

## ADR-005 — Backend hosting: Railway

**Context.** Need simple container deployment for a long-running FastAPI service
with health checks and env management.

**Decision.** **Railway** via `Dockerfile` + `railway.json` (with `/health`).

**Alternatives.** Render; Fly.io; AWS ECS/Fargate; a raw VPS.

**Tradeoffs.** Railway is less configurable than full AWS and can cost more at
scale, but it's the fastest path from Dockerfile to a deployed, health-checked
service with managed env vars — ideal for a portfolio/early-stage product. The
Dockerfile keeps us portable (any container host) if we outgrow it.

---

## ADR-006 — Frontend hosting: Vercel

**Context.** The frontend is Next.js (App Router); we want zero-config builds,
preview deployments per PR, and a global CDN.

**Decision.** **Vercel** via `vercel.json`.

**Alternatives.** Netlify; self-hosting Next on Railway/Node; static export.

**Tradeoffs.** Vercel couples us to its platform for the best Next.js experience
(though Next is portable). In return: first-class Next support, automatic preview
URLs for PRs, edge CDN, and trivial env management — exactly what a fast-iterating
frontend wants.

---

## Cross-cutting note

The recurring theme: **managed platforms + portable artifacts**. We lean on
Supabase/Railway/Vercel to move fast, but keep escape hatches (a Dockerfile,
standard Postgres, portable Next.js, a model-agnostic LLM layer) so no single
vendor is load-bearing if requirements change.
