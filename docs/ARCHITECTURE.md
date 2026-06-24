# LearnGraph — Architecture

This document explains the system design, the agent graph, memory model, and the
deployment topology. It is intended both as engineering documentation and as a
reference for technical interviews.

## 1. System overview

LearnGraph is a multi-agent learning assistant. The core is a **LangGraph
`StateGraph`** running inside a FastAPI service. A **supervisor** node inspects
the conversation and routes the task to one of several **specialist agents**.
Each specialist is a ReAct-style loop that can call **tools** and read/write
**memory**. Results stream back to a Next.js client token-by-token.

```
Next.js (Vercel)  ──HTTP/SSE──►  FastAPI (Railway)  ──►  LangGraph engine  ──►  Supabase/Postgres
```

## 2. The agent graph

File: `backend/app/agents/graph.py`

```
        ┌─────────┐
        │  START  │
        └────┬────┘
             ▼
        ┌─────────┐     produces a structured plan + chooses a route hint
        │ planner │
        └────┬────┘
             ▼
        ┌────────────┐   classifies intent → tutor | quiz | roadmap |
        │ supervisor │   resume | interview | general
        └────┬───────┘
   ┌─────────┼───────────┬───────────┬──────────┬───────────┐
   ▼         ▼           ▼           ▼          ▼           ▼
 tutor     quiz       roadmap     resume    interview    (general)
  agent    agent       agent       agent      agent
   └─────────┴───────────┴─────┬─────┴──────────┴───────────┘
                               ▼
                       ┌──────────────┐  agent requested a tool call?
                       │  should_act  │──yes──► ┌──────────┐
                       └──────┬───────┘          │ ToolNode │──┐
                              │ no               └──────────┘  │ (loops back
                              ▼                                 │  to the agent)
                       ┌──────────────┐ ◄───────────────────────┘
                       │   analysis   │  reflect on tool results
                       └──────┬───────┘
                              ▼
                       ┌──────────────┐  persist goals/progress/quiz/prefs
                       │ memory_update│
                       └──────┬───────┘
                              ▼
                       ┌──────────────┐
                       │   respond    │
                       └──────┬───────┘
                              ▼
                           ┌─────┐
                           │ END │
                           └─────┘
```

- **planner** — turns the raw request into a short structured plan and a route hint.
- **supervisor** — conditional routing to a specialist (LangGraph `add_conditional_edges`).
- **specialists** — Tutor, Quiz, Roadmap, Resume, Interview; each is a ReAct loop bound to a relevant subset of tools.
- **ToolNode** — executes any tool calls the LLM requested, appends `ToolMessage`s, loops back.
- **analysis** — the agent reflects on tool output before answering.
- **memory_update** — writes durable facts (goals, completed topics, quiz scores, preferences) to Supabase.
- **respond** — emits the final assistant message (streamed).

### Human-in-the-loop
High-impact routes (currently **roadmap** and **resume**) pause for approval
before their result is persisted. After the specialist produces its answer, the
graph routes to a ``human_approval`` node that calls LangGraph's ``interrupt()``.
The run pauses (state saved by the checkpointer), the streaming API surfaces an
``interrupt`` event with the approval payload, and the client shows Approve/Reject.
On the user's decision the run resumes via ``/chat/resume`` with
``Command(resume={"approved": bool})`` and continues from exactly where it paused
(workflow recovery). The set of gated routes is ``HIGH_IMPACT_ROUTES`` in
``app/agents/nodes.py``.

## 3. Model selection (swap any LLM via config)

File: `backend/app/agents/models.yaml` + `backend/app/agents/models.py`

```yaml
default: gpt-5
models:
  gpt-5:
    provider: openai
    model: gpt-5
  claude:
    provider: anthropic
    model: claude-sonnet-4-5
  gemini:
    provider: google_genai
    model: gemini-2.5-pro
  deepseek:
    provider: deepseek
    model: deepseek-chat
```

`get_chat_model(name)` reads this registry and returns a LangChain chat model via
`init_chat_model`, so switching models is a one-line config change — no code edits.
Set `LEARNGRAPH_DEFAULT_MODEL` to override the default at runtime.

## 4. Memory

| Type | Scope | Storage | File |
|---|---|---|---|
| Short-term | current thread/session | LangGraph `PostgresSaver` checkpointer | `backend/app/memory/checkpointer.py` |
| Long-term | per user, durable | Supabase tables (`learner_profiles`, `topic_progress`, `quiz_results`, `roadmaps`) | `backend/app/memory/long_term.py` |

The checkpointer is keyed by `thread_id` (one per conversation), enabling
**workflow recovery** — a crashed or interrupted run resumes from its last
checkpoint. Long-term memory is loaded into the graph state at the start of each
run and persisted by the `memory_update` node.

## 5. Tools

All tools live in `backend/app/tools/` and are plain LangChain `@tool` functions,
so any agent can be granted any subset.

1. `web_search` — Tavily (falls back to a stub if no key).
2. `youtube_learning` — YouTube Data API search for tutorials.
3. `roadmap_generator` — LLM-built dependency-ordered learning plan.
4. `quiz_generator` — adaptive MCQ/short-answer quiz with answer key.
5. `resume_review` — ATS-style analysis + suggestions.
6. `interview_prep` — mock interview question generation + rubric.
7. `dsa_mentor` — explanations, hints (not full solutions), practice plans.
8. `progress_analytics` — computes XP, streaks, mastery from stored data.
9. `notes_generator` — structured study notes (Cornell/outline).
10. `resource_recommender` — books, courses, articles, practice sets.

## 6. API surface (FastAPI)

| Route | Method | Purpose |
|---|---|---|
| `/health` | GET | liveness |
| `/auth/me` | GET | verify Supabase JWT, return user |
| `/chat/stream` | POST | SSE token stream from the agent graph |
| `/chat/resume` | POST | resume an interrupted (HITL) run with approval |
| `/progress/summary` | GET | XP, streak, mastery for dashboard |
| `/progress/event` | POST | record a learning event (topic complete, quiz) |

Auth is enforced by a dependency that validates the Supabase JWT (`api/deps.py`).

## 7. Deployment

- **Backend → Railway** using `backend/Dockerfile` + `backend/railway.json`.
- **Frontend → Vercel** using `frontend/vercel.json` (Next.js App Router).
- **DB/Auth → Supabase**; apply `supabase/schema.sql`.

### Required environment variables

Backend (`backend/.env.example`):
```
OPENAI_API_KEY=
LEARNGRAPH_DEFAULT_MODEL=gpt-5
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
DATABASE_URL=               # Postgres connection for checkpointer
TAVILY_API_KEY=             # optional (web_search)
YOUTUBE_API_KEY=            # optional (youtube_learning)
LANGCHAIN_TRACING_V2=true   # optional (LangSmith)
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=learngraph
CORS_ORIGINS=http://localhost:3000
```

Frontend (`frontend/.env.local.example`):
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## 8. Security
- JWT validation on every protected endpoint; threads namespaced by user id.
- Supabase Row-Level Security so users only read/write their own rows.
- Service-role key is backend-only and never shipped to the browser.
- Per-IP sliding-window rate limiting (tighter budget for LLM/upload endpoints).
- Secure response headers (HSTS, X-Frame-Options, X-Content-Type-Options, CSP,
  Referrer-Policy, Permissions-Policy) on both API and frontend.
- Input validation/sanitization on all request bodies (length caps, allowed
  value sets, control-character stripping, thread-id charset).
- Global exception handler returns sanitized errors (no stack traces leak).
- Startup environment validation fails fast in production if critical config is
  missing; warns (with dev fallbacks) otherwise.
