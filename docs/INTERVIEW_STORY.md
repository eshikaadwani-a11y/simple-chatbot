# Interview Story

A first-person narrative for behavioral + technical interviews. Skim before a call;
the goal is to speak about this project with specifics and honesty.

---

## Why I built it
I wanted to learn how real **agentic systems** are built — not a thin wrapper over a
chat completion, but the things production LLM apps actually need: orchestration,
tools, memory, streaming, human oversight, and cost control. A learning platform was
a good vehicle because it naturally needs several specialized behaviors (tutoring,
quizzing, roadmaps, resume review, interview prep), which pushed me toward a
**multi-agent** design instead of one giant prompt.

## What it is (30-second version)
A LangGraph `StateGraph` where a **supervisor routes each request to a specialist
agent**. Each agent is a ReAct loop that can call tools, retrieve from a knowledge
base (RAG), and read/write memory. It streams token-by-token, pauses for human
approval on high-impact actions, and is deployed with auth, rate limiting, CI/CD,
and observability.

## Technical challenges
1. **Modeling control flow explicitly.** A single agent loop couldn't express
   "route → maybe loop through tools → maybe pause for approval → persist → answer."
   LangGraph's graph with conditional edges and a shared `ToolNode` made the flow
   explicit and testable.
2. **Human-in-the-loop that actually resumes.** Using `interrupt()` + a checkpointer
   so the run pauses, survives, and continues from the exact step on approval —
   wiring the pause/resume through an SSE API and the UI.
3. **Grounding answers (RAG).** Building embeddings → vector search → source-cited
   answers, with a clean production (pgvector) vs. offline (in-memory) split so it
   runs anywhere.
4. **Cost/usage visibility.** Capturing token usage via a LangChain callback and
   turning it into per-request cost and an admin dashboard.

## Engineering tradeoffs I made (and can defend)
- **Three LLM calls per turn** (planner → supervisor → specialist) for cleaner
  routing, at the cost of latency/cost — with a clear path to collapse them or route
  with a smaller model.
- **Relational long-term memory** (typed tables) over a vector store, because the
  data is structured; RAG is reserved for unstructured knowledge.
- **In-process rate limiting** to start (zero infra), with Redis as the documented
  next step.
- **Managed platforms (Supabase/Railway/Vercel) + portable artifacts** (Dockerfile,
  standard Postgres, model-agnostic LLM layer) so no vendor is load-bearing.

## The biggest bug I fixed (my favorite story)
During a self-audit I realized the graph runs **async** (`astream_events`) but I'd
wired a **synchronous** `PostgresSaver` checkpointer. **Every test passed** — because
tests use the in-memory saver — but in production, with `DATABASE_URL` set, the first
chat would have crashed, because a sync checkpointer doesn't implement the async
state methods the async graph calls. I switched to `AsyncPostgresSaver` with an async
connection pool and changed `get_state` to `aget_state`. The lesson: **"tests pass"
isn't "works in prod"**, especially around async/sync boundaries and anything that
only activates with real infrastructure.

Other fixes from the same audit: namespacing the LangGraph `thread_id` by `user_id`
(so users can't read each other's conversation state), resetting the approval flag
each turn (the HITL gate was only firing once per thread), and moving blocking LLM/DB
calls off the event loop.

## Lessons learned
- Make control flow **explicit and testable** — it pays off the moment requirements
  get non-linear (routing, loops, pauses).
- **Async correctness** is subtle; mock-based tests can hide infra-only failures.
- **Graceful degradation** (fallbacks when keys/DB are absent) makes a project
  runnable everywhere and dramatically easier to test and demo.
- **Observability and cost** aren't optional for LLM apps — tokens are money.
- Writing my own **honest audit** taught me more than adding features would have.

## Scaling plan (when asked "what's next?")
Shared **Redis** for rate limiting + caching; a **queue + worker pool** (Celery →
Kafka) for long agent runs with streamed results; **pgvector → a dedicated vector
DB** if semantic workloads grow; **Kubernetes** for autoscaled API and worker pools.
Full write-up in `docs/SCALING.md`.

## If they ask "what would you do differently?"
Collapse planner+supervisor into one structured-output call to cut a third of the
LLM cost; add an **eval harness** (LangSmith datasets) so I can measure agent
quality, not just that the code runs; and get a **live deployment + demo** earlier,
because that's what makes the project tangible to others.
