# Observability

LearnGraph ships three layers of observability: **tracing** (LangSmith),
**product/usage monitoring** (counts of users, agents, tools, features), and
**cost analytics** (token usage → USD). All of it is best-effort and never breaks
a user request.

---

## 1. Tracing — LangSmith

**Setup.** Set in the backend env:
```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=learngraph
```
`configure_observability()` (called at startup) exports these so LangChain/
LangGraph emit traces.

**What you get.**
- **Agent traces:** every run shows the full graph path — `load_memory → planner →
  supervisor → <specialist> → ToolNode → memory_update → respond` — as a tree.
- **Workflow visualization:** node-by-node timing and inputs/outputs in the
  LangSmith UI.
- **Tool execution tracking:** each tool call is a child span with its args and
  result.
- **Failure analysis:** exceptions are captured per node, so you can see exactly
  which tool/agent/LLM call failed and with what input.

**Trace enrichment.** Each run is tagged for filtering (`runtime._config`):
- `run_name = "learngraph-agent"`
- `tags = ["learngraph", "user:<id>"]`
- `metadata = {user_id, thread_id}`

So in LangSmith you can filter runs by user or thread and group by tag.

---

## 2. Monitoring — usage events

Every agent run and feature use records a row in **`usage_events`** (Supabase), or
an in-memory list in dev. Captured via a LangChain callback (`TokenUsageCallback`)
plus explicit calls.

**Tracked:**
| Metric | Source |
|---|---|
| Total users | `learner_profiles` count |
| Active users (7d) | `learner_profiles.last_active` |
| AI requests | `usage_events` where `event_type='chat'` |
| Tool calls | `usage_events` where `event_type='tool'` (+ `tool` name) |
| Resume analyses | `event_type='resume_analysis'` |
| Roadmap generations | chat events with `agent='roadmap'` |
| Quiz attempts | chat events with `agent='quiz'` |
| Most-used agents/tools | grouped counts |

**Where it's recorded.**
- `runtime.stream_response` attaches `TokenUsageCallback` to the run, then (after
  streaming) records one `chat` event (with the chosen agent + token usage) and one
  `tool` event per tool used — off the event loop via `asyncio.to_thread`.
- `routes_resume` records a `resume_analysis` event.

---

## 3. Cost analytics

`TokenUsageCallback` accumulates prompt/completion tokens and the model name across
a run. `estimate_cost()` converts tokens → USD using a configurable per-model price
table (`PRICING_PER_MTOK` in `app/analytics.py`).

**Tracked:** token totals, cost per request (stored per event), cost **today**,
cost **this month**, and a **14-day daily cost series**.

> The prices are **estimates** — update `PRICING_PER_MTOK` to match your provider's
> current pricing. Cost is computed at write time and stored on each event, so
> historical cost stays accurate even if prices change later.

---

## 4. Admin dashboard

`GET /admin/analytics` (backend) returns the aggregated metrics; the frontend
`/admin` page renders them: metric tiles, most-used agents/tools bar charts, and a
daily-cost area chart.

**Access control.** Protected by `require_admin`:
- Production: only emails in `ADMIN_EMAILS` (backend env).
- Non-production with `ADMIN_EMAILS` unset: allowed (dev convenience).
The frontend shows the **Admin** nav link only for emails in
`NEXT_PUBLIC_ADMIN_EMAILS`.

---

## 5. Health & logs
- `GET /health` for liveness (Railway healthcheck).
- Structured startup logs report model, Supabase/DB availability, and whether the
  async Postgres checkpointer initialized.
- A global exception handler logs full tracebacks server-side while returning
  sanitized errors to clients.

---

## 6. What's intentionally deferred
- Metrics export to Prometheus/Grafana or OpenTelemetry (current monitoring is
  Supabase-backed and sufficient for this scale).
- Alerting (e.g. cost spikes) — would layer on the `usage_events` data.
- Per-user cost quotas — the data needed is already captured.
