# Final Engineering Audit

A production-readiness review performed as the engineer who has to put this live.
Scores are **honest and uninflated** (1–10). Issues are tagged **[FIXED]** (done in
this review) or **[OPEN]** (recommended, with the exact fix).

> **The single most important caveat:** this codebase has **never been executed
> end-to-end**. No dependencies were installed, no server was booted, no real LLM/
> Supabase call was made, and it was never deployed. The design is sound and the
> static checks (ruff lint+format, byte-compile) pass, but "compiles and looks
> right" is not "runs in production." Several scores reflect that unproven risk.

---

## Architecture Review — **7/10**

**Strengths.** Clean separation (agents / tools / memory / api / services). Genuine
multi-agent supervisor pattern. Model-agnostic LLM layer. Dual-layer memory. Good
docs.

| Issue | Impact | Likelihood | Fix | Status |
|---|---|---|---|---|
| **3 LLM calls per turn** (planner → supervisor → specialist) | 2–3× latency & cost on every message | High (every request) | Merge planner+supervisor into one structured call, or route with `gpt-5-mini` | OPEN |
| No graph-level timeout / `recursion_limit` tuning | A misbehaving tool loop can run to the default limit (25) | Low | Set `recursion_limit` in config and a wall-clock guard | OPEN |
| Over-engineering vs. current scale | More moving parts to operate than traffic needs | Medium | Acceptable for a portfolio; document as intentional | N/A |

**Why not higher:** the architecture is good but **unproven at runtime**, and the
per-turn LLM overhead is a real cost/latency smell.

---

## Deployment Review — **5/10**

| Issue | Impact | Likelihood | Fix | Status |
|---|---|---|---|---|
| **Sync `PostgresSaver` under async `astream_events`** | Chat/HITL crash in prod when `DATABASE_URL` is set (tests passed because they use `MemorySaver`) | **Was ~certain in prod** | Use `AsyncPostgresSaver` + `AsyncConnectionPool`; use `aget_state` | **[FIXED]** |
| **GPT-5 `temperature` override** | Reasoning models often 400 on non-default temperature → every call fails | High | Removed temperature from gpt-5 entries; added `timeout` | **[FIXED]** |
| SSE buffered by proxy/CDN | Tokens arrive in one chunk, not streamed | Medium | Added `X-Accel-Buffering: no`, `Cache-Control: no-cache` | **[FIXED]** |
| `MemorySaver` fallback hides DB failure | HITL silently non-durable; looks fine then loses state on restart | Medium | Fallback is logged at ERROR; consider failing fast in prod | PARTIAL |
| Unverified dependency version matrix | `pip install` could fail or pull incompatible langgraph/langchain | Medium | Pin from a successful CI lockfile; let CI prove it | OPEN |
| GPT-5 model id may not match your account | 404/400 model-not-found at runtime | Medium | Confirm the exact model name in `models.yaml` | OPEN |
| No frontend lockfile (`package-lock.json`) | Non-reproducible builds; CI/Vercel may resolve different versions | Medium | Commit a lockfile after a clean `npm install` | OPEN |

**Why this low:** until CI runs green and one real deploy succeeds, deployment is
*plausible*, not *proven*. The fixes above remove the known blockers; the residual
risk is "first real run."

---

## Security Review — **7/10**

**Strengths.** JWT verification, Postgres RLS, per-user thread isolation, rate
limiting, secure headers, input validation/sanitization, sanitized errors, prod env
validation.

| Issue | Impact | Likelihood | Fix | Status |
|---|---|---|---|---|
| Rate-limiter unbounded memory (keys never evicted) | Slow memory leak from one-off IPs | Medium | Added periodic sweep + eviction | **[FIXED]** |
| In-process rate limiting | Bypassable across replicas; resets on deploy | High at scale | Back with Redis | OPEN |
| `X-Forwarded-For` trust | IP spoofing to dodge limits if not behind a trusted proxy | Medium | Trust only the LB hop / use a proxy-count config | OPEN |
| No audit logging of sensitive actions | Harder incident response | Low | Structured audit log for auth/resume/HITL | OPEN |
| Service-role key bypasses RLS | A backend query missing a `user_id` filter would leak data | Low (all current queries filter) | Keep RLS as defense-in-depth; add a test asserting per-user isolation | OPEN |

---

## Database Review — **6/10**

**Strengths.** Sensible relational schema, RLS policies, signup trigger,
`updated_at` trigger, pooler-friendly (`prepare_threshold=0`).

| Issue | Impact | Likelihood | Fix | Status |
|---|---|---|---|---|
| No migration tooling (single `schema.sql`) | Schema drift; no versioned rollouts | Medium | Adopt Supabase migrations / Alembic-style versioning | OPEN |
| Dev-user (`"dev-user"`) vs. `uuid` columns | Insert fails if Supabase configured but JWT secret absent | Low (unusual config) | Require JWT secret whenever Supabase is set (env validation) | OPEN |
| Few indexes beyond `user_id` | Slow analytics as rows grow | Low now | Add composite indexes (`user_id, taken_at`) when needed | OPEN |
| `goals` jsonb dedup only in app | Possible duplicates if written elsewhere | Low | Enforce in a single writer / normalize to a table | OPEN |

---

## LangGraph Review — **7/10**

**Strengths.** Correct `StateGraph`, conditional routing, shared `ToolNode`, ReAct
loop, real `interrupt()`/`Command(resume=...)`, checkpointer-backed recovery, and a
test that drives the interrupt/resume cycle.

| Issue | Impact | Likelihood | Fix | Status |
|---|---|---|---|---|
| Async/sync checkpointer + `get_state` mismatch | Runtime errors in prod | Was high | `AsyncPostgresSaver` + `aget_state` | **[FIXED]** |
| Routing back through `tools → specialist` recompiled each turn | Minor inefficiency | Low | Acceptable | N/A |
| No structured tool-output schemas | LLM may mis-parse tool JSON | Low–Med | Pydantic tool args/return types | OPEN |
| No eval harness for agent quality | Quality regressions go unnoticed | Medium | LangSmith datasets + scored runs in CI | OPEN |

---

## Multi-Agent Review — **6/10**

**Strengths.** Real supervisor + five scoped specialists; clean tool partitioning.

| Issue | Impact | Likelihood | Fix | Status |
|---|---|---|---|---|
| Routing = one-word LLM classification | Brittle; mis-routes ambiguous requests | Medium | Few-shot examples or structured-output classifier; confidence fallback to `general` | OPEN |
| Single-hop delegation only (no agent↔agent) | Can't compose (e.g. roadmap → quiz) in one turn | Medium | Allow supervisor re-entry / handoff edges | OPEN |
| No per-specialist failure handling | A failing specialist ends the turn with a raw error | Low | Try/fallback to `general` agent | OPEN |

---

## Frontend Review — **6/10**

**Strengths.** Next.js App Router, Supabase auth, streaming chat with live agent/
tool indicators + HITL approval, dashboard with charts, resume upload, error/404/
loading states, security headers.

| Issue | Impact | Likelihood | Fix | Status |
|---|---|---|---|---|
| Supabase client `!` assertion crashed app if env missing | White screen at import | Medium | Guard + safe placeholder + warning | **[FIXED]** |
| Thin tests (only pure helpers) | UI regressions uncaught | Medium | Add React Testing Library + Playwright E2E | OPEN |
| `npm run build` never executed here | Build could fail on a type/SSR issue | Medium | Let frontend CI prove it | OPEN |
| Accessibility not audited | a11y gaps | Low | Run axe/Lighthouse; label inputs | OPEN |

---

## Backend Review — **7/10**

**Strengths.** Clean FastAPI structure, DI auth, validation, security middleware,
typed settings, graceful fallbacks.

| Issue | Impact | Likelihood | Fix | Status |
|---|---|---|---|---|
| Blocking LLM/DB calls in async routes (`/progress`, `/resume`) | One slow call blocks the whole worker | High under load | Wrapped in `run_in_threadpool` | **[FIXED]** |
| Broad `except Exception` in several places | Masks root causes | Low | Narrow exceptions / add error codes | OPEN |
| No request IDs / structured logging | Hard to trace prod issues | Medium | Add correlation IDs + JSON logs | OPEN |
| `/health` doesn't check DB/LLM readiness | LB marks healthy while deps are down | Low | Add a `/health/ready` deep check | OPEN |

---

## Testing Review — **6/10**

**Strengths.** Meaningful backend suite: routing, planner, nodes, **full-graph HITL
interrupt/resume**, memory/analytics, all tools, auth, API, security — all runnable
offline with mocks.

| Issue | Impact | Likelihood | Fix | Status |
|---|---|---|---|---|
| Coverage never measured; 70% gate may fail first run | Red CI on the PR | Medium | Run locally; adjust gate or add tests | OPEN |
| No real-LLM integration/smoke test | Prompt/model regressions invisible | Medium | One gated nightly test with a real key | OPEN |
| Frontend tests cover 2 helpers only | Low real UI coverage | Medium | RTL component tests + Playwright | OPEN |
| Tests not executed in this environment | Unknown unknowns | Medium | CI is the first execution | OPEN |

---

## Documentation Review — **8/10**

**Strengths.** README with diagram, `ARCHITECTURE.md`, `DECISIONS.md` (ADRs),
`SCALING.md`, interview guide + 50-question bank. This is a top strength.

| Issue | Impact | Likelihood | Fix | Status |
|---|---|---|---|---|
| No screenshots committed | Less visual punch | n/a | Capture after first local run (`docs/assets/README.md`) | OPEN |
| Some docs describe intended (not yet verified) behavior | Slight over-promise | Low | Add a "status: unverified at runtime" note where relevant | PARTIAL |
| No API reference beyond OpenAPI | Minor | Low | Link `/docs` (Swagger) in README | OPEN |

---

## Score summary

| Section | Score |
|---|---:|
| Architecture | 7 |
| Deployment | 5 |
| Security | 7 |
| Database | 6 |
| LangGraph | 7 |
| Multi-Agent | 6 |
| Frontend | 6 |
| Backend | 7 |
| Testing | 6 |
| Documentation | 8 |
| **Weighted overall** | **6.5 / 10** |

**Bottom line.** As a portfolio/intern project this is **strong** — well above a
typical student submission in breadth, structure, and engineering practices. As a
*production system today* it's **not there yet**: the gating items are (1) prove CI
green, (2) one successful real deploy, (3) confirm the GPT-5 model id and a live
chat round-trip with the new async checkpointer. Do those three and the realistic
overall moves toward **8/10**.
