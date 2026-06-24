# Recruiter-Facing Assessment

An honest read of how this project lands with recruiters and engineers, and how it
stacks up for internships. Written to be useful, not flattering.

---

## 1. What makes this project impressive?
- It's a **real agentic system**, not a "call the OpenAI API" wrapper: a LangGraph
  supervisor routes to five specialized agents that reason and call tools.
- **Production engineering, not just an ML demo:** auth, RLS, rate limiting, secure
  headers, CI/CD with a coverage gate, Dockerized deploy, error handling.
- **Hard, current concepts done correctly:** human-in-the-loop via graph
  interrupts, dual-layer memory (Postgres checkpointer + relational long-term
  store), token streaming, a model-agnostic config layer.
- **Excellent documentation:** architecture diagram, ADRs, a scaling plan, and an
  interview prep bank — signals communication and seniority.

## 2. What would senior engineers like?
- **Explicit, testable control flow** (the graph) instead of a hidden agent loop.
- **Separation of concerns** and a clean dependency-injected FastAPI layer.
- **Self-awareness:** a `FINAL_AUDIT.md` that names the project's own weaknesses
  (e.g. the async checkpointer bug, per-turn LLM cost) reads as maturity.
- **Thoughtful tradeoffs** documented in `DECISIONS.md` (managed platforms +
  portable artifacts; relational memory now, vectors later).

## 3. What would recruiters like?
- A crisp one-liner that maps to in-demand keywords: *multi-agent, LangGraph,
  GPT-5, FastAPI, Next.js, Supabase, CI/CD*.
- Visible engineering rigor (CI badges, tests, security) that de-risks the hire.
- A repo that's **readable without running it** — diagram, README, docs.

## 4. What weaknesses would they notice?
- **Not yet proven to run/deploy.** No live demo URL, no screenshots, CI not yet
  green. This is the biggest gap — a working deployed link would change the
  perception significantly.
- **Per-turn cost/latency** (planner + supervisor + specialist = 3 LLM calls).
- **Routing is a brittle one-word LLM classification**; no agent-to-agent
  composition.
- **Test coverage is unproven** and frontend tests are thin (pure helpers only).
- **Single-instance assumptions** (in-process rate limiting) — fine for a demo,
  flagged for scale.
- Some breadth may read as **over-engineering** relative to traffic — defensible if
  you frame it as a learning/portfolio goal.

## 5. Likely interview questions
(Full bank: `docs/INTERVIEW_QUESTIONS.md`.) The ones most likely to come up here:
- "Walk me through what happens on one chat request." (know the graph cold)
- "Why LangGraph over a single ReAct agent or a chain?"
- "How does human-in-the-loop actually work — what pauses, what persists, how do
  you resume?"
- "Sync vs async: why did the Postgres checkpointer matter?" (great story — you
  found and fixed a real async/sync bug)
- "How do you isolate one user's conversation from another's?"
- "Where does this break at 10×/100× traffic, and what do you change?"
- "It makes three LLM calls per message — how would you cut cost?"
- "How would you evaluate whether the agents are actually good?"

> Tip: lead with the **async-checkpointer bug you caught in your own audit**. "Tests
> passed but prod would've crashed because the async graph used a sync checkpointer;
> I switched to `AsyncPostgresSaver` and `aget_state`." That single story
> demonstrates debugging, async understanding, and production thinking.

## 6. Resume bullet to use
**Recommended (medium):**
> Built a production-grade multi-agent AI tutor with LangGraph and GPT-5: a
> supervisor routes requests to five specialized ReAct agents backed by 10 tools,
> long-term Supabase memory, a Postgres checkpointer for stateful recovery, and
> token-streaming APIs — shipped with JWT auth, rate limiting, CI/CD, and tests.

(Short and advanced variants in `docs/INTERVIEW_GUIDE.md`.)

---

## Overall scores for internships (out of 10)

| Track | Score | Rationale |
|---|---:|---|
| **SWE internships** | **8** | Full-stack breadth, CI/CD, tests, security, clean structure. Loses points for no live demo + unverified runtime. |
| **Backend internships** | **8** | Strong: FastAPI, async, Postgres/RLS, auth, rate limiting, streaming, deploy config. Same demo/runtime caveat. |
| **AI engineering internships** | **8.5** | Genuinely differentiated: multi-agent orchestration, tool-calling, memory, HITL, observability. The most impressive angle. |
| **Startup internships** | **8.5** | Ship-fast, end-to-end ownership, pragmatic managed stack, product surface (dashboard, resume tool). Exactly the profile startups want. |

**What moves every score to ~9+:** (1) a **live deployed demo link**, (2) **green
CI** proving it builds/tests, (3) **screenshots/GIF** in the README. None require
new features — just finishing deployment and capturing evidence.

---

## Compared to typical student projects

| Dimension | Typical student project | LearnGraph |
|---|---|---|
| Scope | One feature / CRUD app / API wrapper | Full multi-agent platform, front-to-back |
| AI usage | Single prompt → response | Supervisor + specialists + tools + memory + HITL |
| Testing | None or a couple of tests | Backend suite incl. graph/HITL; coverage gate |
| Ops | Runs on localhost | Dockerized, CI/CD, deploy configs, security middleware |
| Docs | A thin README | README + diagram + ADRs + scaling + interview prep |
| Self-assessment | None | Honest audit naming its own bugs/tradeoffs |

**Verdict.** Clearly **top-decile** for an intern portfolio in *engineering breadth,
production practices, and communication*. The one thing standing between "very
impressive repo" and "obviously hireable, look at the live demo" is **finishing the
deploy and capturing proof it runs** — which is exactly where the
`DEPLOYMENT_AUDIT.md` checklist takes you.
