# 3-Minute Recruiter Demo Script

A tight, rehearsed walkthrough that shows the strongest engineering in ~3 minutes.
Each step has **what to do**, **what to say**, and **what it proves**. Total ≈ 3:00.

> Prep: be logged in on a second account with some history so the dashboard isn't
> empty. Have a sample PDF resume ready. Open DevTools → Network for the streaming
> moment. Your account should be in `ADMIN_EMAILS` for the analytics step.

---

## 0:00–0:20 — One-liner + login
**Do:** Show the landing page, click Log in.
**Say:** "LearnGraph is a multi-agent AI learning platform — GPT-5 and LangGraph on
the backend, Next.js on the front. A supervisor routes each request to a specialist
agent: tutor, quiz, roadmap, resume, or interview."
**Proves:** Clear product framing; full-stack scope.

## 0:20–0:45 — Dashboard
**Do:** Land on the dashboard; point at XP, streak, mastery chart, weak areas.
**Say:** "Everything's personalized from long-term memory in Postgres — goals,
completed topics, quiz history — so the agents adapt to the learner."
**Proves:** Persistence + stateful personalization, not a stateless chatbot.

## 0:45–1:20 — Roadmap + human-in-the-loop (the highlight)
**Do:** In chat, type *"Build me an 8-week roadmap to learn backend engineering."*
Show tokens streaming. When the **Approve / Reject** prompt appears, pause.
**Say:** "Notice it's streaming token-by-token over SSE. And before it saves this
roadmap, the graph **pauses for my approval** — that's a real LangGraph
`interrupt()`; the run is checkpointed and resumes exactly where it stopped when I
approve." Click **Approve**.
**Proves:** Streaming, human-in-the-loop, durable/resumable workflows — the hardest,
most senior-signal features.

## 1:20–1:50 — Knowledge-grounded answer (RAG)
**Do:** Ask *"Explain the two-pointer technique and when to use it."* Point at the
cited source.
**Say:** "The tutor agent first retrieves from a curated knowledge base via a vector
search, then answers and **cites the source** — so it's grounded, not hallucinated."
**Proves:** RAG pipeline (embeddings → vector search → grounding) — the key
AI-engineering skill.

## 1:50–2:20 — Resume analysis
**Do:** Go to Resume, upload the sample PDF, show the ATS score ring + bullet
rewrites.
**Say:** "Upload a PDF — we parse it, run it through the resume agent, and return an
ATS score, a skill gap, and quantified bullet rewrites."
**Proves:** File handling, a second real tool surface, practical value.

## 2:20–2:45 — Interview coaching
**Do:** Ask *"Run a mock backend interview, one system-design question."* Show the
question + rubric.
**Say:** "The interview agent generates realistic questions with grading rubrics and
grounds technical answers in the same knowledge base."
**Proves:** Multi-agent breadth; consistent grounding.

## 2:45–3:00 — Admin analytics + close
**Do:** Open `/admin`. Point at users, agent/tool usage, and **LLM cost** charts.
**Say:** "And it's observable: every run is traced in LangSmith, and this dashboard
tracks usage and **real token cost** per day. It's deployed on Railway and Vercel
with CI/CD and tests."
**Proves:** Production maturity — observability, cost awareness, ops.

---

## If you only have 60 seconds
Login → **roadmap with the human-in-the-loop approval** (streaming + interrupt) →
**RAG-cited answer** → **admin cost dashboard**. Those three beats carry the whole
story.

## Backup talking points (if asked)
- "Tests passed but prod would've crashed" → the async-checkpointer bug you caught
  in your own audit (great signal).
- Model-agnostic: "swap GPT-5 for Claude/Gemini in one config line."
- Scaling: "shared Postgres checkpointer scales horizontally; Redis + a queue is the
  next step — it's written up in `docs/SCALING.md`."

## Demo failure recovery
- If streaming looks buffered: mention SSE anti-buffering headers and that a proxy
  may still buffer; show the final answer.
- If an LLM call errors: show the sanitized error handling and the LangSmith trace
  of the failure — "even failures are observable."
