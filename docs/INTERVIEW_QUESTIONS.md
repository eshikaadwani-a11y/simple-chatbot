# Interview Question Bank (50 Q&A)

Questions and concise answers grounded in this project. Use them to rehearse;
expand any answer with code references from `backend/app/`.

---

## LangGraph (1–8)

**1. What is LangGraph and why use it over a plain chain?**
A library for building agents as a graph of nodes with explicit shared state and
edges. Unlike a linear chain, it supports cycles (ReAct loops), conditional
routing, durable checkpoints, and human-in-the-loop pauses — control flow you can
inspect and test.

**2. What is a `StateGraph`?**
A graph whose nodes read and write a typed shared state object. Each node returns a
partial update; reducers merge updates into the channels. Here the state is
`AgentState` (`agents/state.py`).

**3. How does the `messages` channel accumulate history?**
It uses the `add_messages` reducer, so each node *appends* messages instead of
overwriting — essential for the ReAct loop and multi-turn context.

**4. How is conditional routing implemented?**
`add_conditional_edges(node, router_fn, mapping)`. The supervisor returns a route
string; the router maps it to `agent_<route>`. After a specialist step,
`tools_condition` decides tools vs. finish.

**5. What does the `ToolNode` do?**
It executes any tool calls the LLM emitted, appends `ToolMessage`s, and returns to
the agent. Injected args (e.g. `user_id` via `InjectedState`) are filled
automatically so the LLM never supplies them.

**6. How does short-term memory / recovery work?**
A checkpointer snapshots state after each step, keyed by `thread_id`. A crashed or
interrupted run resumes from its last checkpoint. We use `PostgresSaver` in prod,
`MemorySaver` as a dev fallback.

**7. How is human-in-the-loop implemented?**
A `human_approval` node calls `interrupt(payload)`. The graph pauses and persists;
the API surfaces the payload; the run resumes with
`Command(resume={"approved": ...})` from the interrupt point.

**8. A bug you hit with checkpointed state?**
`approved` persisted across turns, so the approval gate only fired once per thread.
Fix: reset it in `load_memory` each turn. Also namespaced `thread_id` by `user_id`
to prevent cross-user resume.

---

## FastAPI (9–14)

**9. Why FastAPI here?**
Native async, first-class streaming (SSE), Pydantic validation, dependency
injection for auth, and auto-generated OpenAPI docs.

**10. How do you stream tokens to the browser?**
`sse-starlette`'s `EventSourceResponse` wraps an async generator yielding SSE
frames; the agent runtime yields typed events (`token`, `tool`, `route`,
`interrupt`, `done`).

**11. How is auth enforced?**
A dependency (`get_current_user`) validates the Supabase JWT (HS256, `aud
=authenticated`) and returns the user; protected routes `Depends` on it.

**12. How do you validate input?**
Pydantic models with length caps, `Literal` value sets, regex for `thread_id`, and
a validator that strips control characters. Multipart uploads check content-type
and size.

**13. How do you handle errors globally?**
A registered exception handler logs the traceback server-side and returns a
sanitized JSON message — clients never see stack traces. Validation errors return
a clean 422.

**14. Sync vs async in your nodes?**
LLM/tool calls are synchronous but run inside LangGraph's threadpool when invoked
via `astream_events`, so they don't block the event loop. Acceptable because LLM
latency dominates; would go fully async under heavy concurrency.

---

## AI Agents (15–21)

**15. What is the ReAct pattern?**
Reason → Act (call a tool) → Observe (tool result) → repeat → answer. Implemented
as agent ↔ `ToolNode` cycles until the model stops requesting tools.

**16. What is the supervisor pattern?**
A router agent classifies intent and delegates to a specialist. Keeps each
specialist's prompt and tool set focused, improving quality and cost vs. one
mega-agent.

**17. How do agents get the right tools?**
`TOOLS_BY_AGENT` maps each specialist to a tool subset; the node binds only those
via `bind_tools`. All tools live in a shared `ToolNode`.

**18. How do you prevent prompt-injection via tool output?**
Tools return structured JSON, never raw HTML/scripts; tool errors are caught and
returned as data; the agent treats tool output as untrusted content to summarize,
not instructions to obey. (Hardening tool-output schemas is a documented next step.)

**19. How do you keep the agent personalized?**
`load_memory` injects a compact long-term snapshot (goals, completed topics, XP,
prefs) into the specialist's system prompt at run start.

**20. How would you evaluate agent quality?**
LangSmith datasets + scored runs: curate representative prompts, assert routing,
tool selection, and answer rubrics; track regressions in CI. (Planned.)

**21. How do you make the LLM swappable?**
A YAML registry maps logical names to providers; `init_chat_model` resolves them.
Changing `default:` (or `LEARNGRAPH_DEFAULT_MODEL`) swaps GPT-5 ↔ Claude/Gemini/
DeepSeek with no code change.

---

## System Design (22–28)

**22. Walk me through a chat request end-to-end.**
Frontend POSTs to `/chat/stream` with JWT → auth dependency → graph: load_memory →
planner → supervisor → specialist (ReAct tool loop) → optional human_approval →
memory_update → respond. Tokens stream back over SSE.

**23. Where is state, and why does that enable scaling?**
Per-request state lives in the checkpointer (Postgres), not the process. So any
instance can handle any user's thread; you scale FastAPI horizontally behind a LB.

**24. What breaks first under load?**
In-process rate limiter (not shared) and LLM concurrency/latency. Fixes: Redis for
limits/cache, a queue + worker pool for long runs.

**25. How would you add background jobs?**
Enqueue agent runs to Redis/Celery (or Kafka at scale); workers run the graph and
publish streamed events via pub/sub. See `SCALING.md`.

**26. How do you stream from background workers?**
Workers publish token events to a Redis pub/sub channel keyed by thread; the API
subscribes and relays over SSE/websocket to the client.

**27. How do you control LLM cost?**
Model tiering (route easy tasks to `gpt-5-mini`), cache deterministic tool calls,
cap streaming concurrency, and use backpressure via the queue.

**28. How would you add semantic memory?**
Embed notes/history into pgvector (stay on Postgres) for retrieval-augmented recall
and recommendations; graduate to a dedicated vector DB if it outgrows Postgres.

---

## Databases (29–34)

**29. Why Postgres/Supabase over NoSQL?**
The data is relational and structured (profiles, scores, XP, roadmaps) and queried
by user id — a good fit for SQL + constraints. Supabase adds managed auth + RLS.

**30. What is Row-Level Security and how do you use it?**
Postgres policies that restrict row access by predicate. Each table has
`auth.uid() = user_id` policies so users can only touch their own rows.

**31. If RLS exists, why also filter by user_id in the backend?**
The backend uses the **service-role key**, which bypasses RLS. So it must filter by
the authenticated `user_id` itself; RLS is defense-in-depth for any client using
the anon key.

**32. How is a profile created on signup?**
A trigger (`on_auth_user_created`) inserts a `learner_profiles` row when a new
`auth.users` row appears.

**33. How is streak logic computed?**
On XP award, compare `last_active` to today: same day → no change, yesterday →
increment, older → reset to 1. Stored on the profile.

**34. Where do LangGraph checkpoints live?**
In Postgres tables created by `PostgresSaver.setup()` — separate from the domain
tables, keyed by thread.

---

## Security (35–40)

**35. How are passwords/tokens handled?**
Supabase Auth manages credentials and issues JWTs; the backend only verifies
tokens. The service-role key stays server-side and never reaches the browser.

**36. How do you stop a user reading another's conversation?**
`thread_id` is namespaced by `user_id` before hitting the checkpointer, so thread
state is partitioned per user.

**37. What rate limiting did you implement?**
A per-IP sliding-window limiter with a tighter budget for LLM/upload endpoints,
returning 429 + `Retry-After`. In-process now; Redis for multi-instance.

**38. Which security headers and why?**
HSTS (force HTTPS), X-Content-Type-Options (no MIME sniffing), X-Frame-Options/CSP
`frame-ancestors` (clickjacking), Referrer-Policy, Permissions-Policy.

**39. How do you handle file-upload risk?**
Validate content-type and `.pdf`, cap at 5 MB, parse in a sandboxed lib (pypdf),
and reject unreadable/empty extractions with a 422.

**40. How do you avoid leaking internals in errors?**
A global handler logs full detail server-side and returns generic messages.
Production env validation fails fast if secrets are missing.

---

## Deployment (41–45)

**41. How is the backend deployed?**
Dockerized FastAPI on Railway with `railway.json` (Dockerfile builder, `/health`
check, restart policy). `$PORT` is provided by Railway.

**42. How is the frontend deployed?**
Next.js on Vercel (`vercel.json`), with public env vars set in the dashboard and
preview deployments per PR.

**43. How do you manage secrets/config?**
12-factor env vars via `pydantic-settings`; `.env.example` documents them; real
values live in Railway/Vercel/Supabase, never in git.

**44. What must change for multi-instance backend?**
Use the Postgres checkpointer (not in-memory) and move rate limiting to Redis so
state and limits are shared.

**45. How do you do health checks / zero-downtime?**
`/health` endpoint drives Railway's healthcheck; rolling deploys replace instances
only after health passes.

---

## CI/CD (46–50)

**46. What does your CI run?**
Backend: ruff lint + format check, mypy, pytest with a 70% coverage gate. Frontend:
eslint, `tsc --noEmit`, vitest, `next build`.

**47. Why path-filtered workflows?**
Backend-only changes shouldn't run frontend CI (and vice-versa) — faster feedback
and less wasted compute.

**48. How do tests run without external services?**
The LLM and Supabase are mocked; the app falls back to in-memory stores. A
`FakeLLM` returns deterministic routing/answers so the graph (incl. HITL) is
tested offline.

**49. How do you test the human-in-the-loop flow?**
Build the graph with `MemorySaver`, invoke until it pauses at `human_approval`,
assert the interrupt, then `invoke(Command(resume={"approved": True}))` and assert
completion + `approved`.

**50. What's the value of a coverage gate?**
It makes "we have tests" enforceable: a PR that drops coverage below 70% fails CI,
so coverage can't silently erode as the codebase grows.
