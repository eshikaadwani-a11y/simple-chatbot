# The 10/10 Plan

Brutally honest. No low-impact features. This is what actually separates "very
impressive repo" from "recruiter stops scrolling and books the call."

---

## 1. Current project rating

| Lens | Rating | Notes |
|---|---:|---|
| Code & design quality | **8.5–9** | Multi-agent LangGraph, RAG, dual-layer memory, HITL, observability/cost, security, CI/CD, tests, strong docs. |
| Verifiable artifact (what a recruiter can confirm) | **~7.5** | Still **not deployed**, no live demo, CI not yet proven green, no screenshots. |
| **Realistic overall today** | **~8** | The engineering is genuinely strong; the gap is *proof it runs*, not capability. |

This round added the highest-leverage engineering: **RAG grounding**,
**observability + cost analytics**, and **deployment hardening** (the async
checkpointer fix alone removed a guaranteed prod crash). Those raised the ceiling.
The floor is still set by "unproven at runtime."

---

## 2. Remaining weaknesses (honest)

1. **Not deployed / no live demo link.** The single biggest gap. Everything else is
   secondary to this.
2. **CI never run green.** Tests/build are written to pass but have not executed in
   this environment; the first run is the proof.
3. **No screenshots / GIF.** A recruiter shouldn't have to imagine the UI.
4. **Agent quality is unmeasured.** There's no eval harness, so "the agents are
   good" is an assertion, not data.
5. **3 LLM calls per turn** (planner → supervisor → specialist): real latency/cost
   overhead.
6. **Frontend tests are thin** (pure helpers only); no component/E2E coverage.
7. **Single-instance assumptions** (in-process rate limiting) — fine for launch,
   flagged for scale.

---

## 3. Highest-impact improvements (ranked, NOT new features)

### A. Deploy it live + add a demo link and a GIF — **biggest jump**
Follow `docs/DEPLOYMENT_VERIFICATION.md` end to end. Put the live URL at the top of
the README and a 20–30s screen-capture GIF of the roadmap → human-approval → RAG
flow. *Why:* converts "impressive code" into "I can click it." Worth more than any
feature.

### B. Get both CI workflows green and add the badges (already in README)
Run `pytest --cov`, fix any coverage/build gaps, push. *Why:* proves the tests and
build are real, not decorative.

### C. Add a small evaluation harness
A handful of LangSmith dataset cases asserting routing + answer rubrics, run in CI
(or nightly with a real key). *Why:* "I measure agent quality and guard against
regressions" is a senior AI-engineering signal — and directly addresses weakness #4.

### D. Cut the per-turn LLM cost
Collapse planner+supervisor into one structured-output classification, or route with
`gpt-5-mini`. *Why:* shows cost/latency awareness; you can quote a before/after
number from the cost dashboard you already built.

### E. A few real frontend tests
2–3 React Testing Library component tests + one Playwright E2E of the login→chat
path. *Why:* rounds out the "tests exist across the stack" story.

> Items A–B are **proof**, not building. C–E are **polish**. None are new product
> features — exactly per the brief.

---

## 4. Expected rating after completion

| After | SWE | Backend | AI Eng | Startup |
|---|---:|---:|---:|---:|
| Today | 8 | 8 | 8.5 | 8.5 |
| + A & B (deploy + green CI + demo) | 9 | 9 | 9.5 | 9.5 |
| + C, D, E (evals, cost cut, FE tests) | 9.5 | 9.5 | **10** | **10** |

For **AI-engineering and startup** internships this becomes a genuine **10**: a
deployed, observable, cost-aware, evaluated multi-agent RAG system is exactly the
profile those roles hire for. For **SWE/backend** it lands **9.5** — elite for an
intern portfolio — with the deployment + tests doing the heavy lifting.

---

## 5. Why these improvements matter (and others don't)

- **Recruiters trust what they can verify.** A live link + green CI + a GIF move the
  project from "claims" to "evidence." That's the entire difference between 8 and 10
  for most reviewers.
- **AI-engineering hiring rewards the full loop:** retrieval, orchestration,
  observability, **and** evaluation. You now have the first three; evals complete
  the picture.
- **Cost awareness reads as production maturity.** You built the cost dashboard —
  using it to *reduce* cost is a great interview anecdote.
- **What to NOT do:** more agents, more tools, more pages. Breadth is already a
  strength bordering on over-engineering; additional features would *lower* the
  signal-to-noise, not raise the score.

---

## Bottom line
The code is already top-decile for an intern portfolio. The remaining points are
earned by **proving it runs** (deploy + CI + demo) and **measuring it** (evals),
plus a small cost/test polish — not by adding anything new. The last mile
(deployment + demo) requires your live credentials and a browser, so it's on you;
the runbook in `docs/DEPLOYMENT_VERIFICATION.md` makes it mechanical.
