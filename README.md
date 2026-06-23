# 🧠 LearnGraph — Multi-Agent AI Learning Platform

> Built a multi-agent AI learning platform using **GPT-5, LangGraph, FastAPI, Next.js, Supabase, and Railway**. Implemented tool-using autonomous agents, long-term memory, personalized learning workflows, progress analytics, and multi-agent orchestration.

LearnGraph is a **production-grade agentic platform** — not a prompt-response chatbot. It uses a **LangGraph `StateGraph`** with a **supervisor that delegates to specialized agents** (Tutor, Quiz, Roadmap, Resume, Interview), each backed by real tools, short- and long-term memory, streaming responses, human-in-the-loop checkpoints, and LangSmith observability.

---

## ✨ Highlights (resume-worthy)

| Capability | How it's implemented |
|---|---|
| **Multi-agent orchestration** | Supervisor node routes to specialist agents via conditional edges (`backend/app/agents/graph.py`) |
| **ReAct tool-using agents** | Reason → decide → call tool → analyze → respond loop with a `ToolNode` |
| **Model-agnostic** | Swap GPT-5 / Claude / Gemini / DeepSeek via `backend/app/agents/models.yaml` |
| **Long-term memory** | Learner profile, goals, quiz history, roadmap progress in Supabase/Postgres |
| **Short-term memory** | LangGraph checkpointer (Postgres) — workflows resume without losing state |
| **Streaming** | Token-by-token Server-Sent Events from FastAPI → Next.js |
| **Human-in-the-loop** | `interrupt()` checkpoints for approval of high-impact actions |
| **Observability** | LangSmith tracing wired through environment config |
| **Auth** | Supabase Auth (JWT) with protected routes on both backend and frontend |
| **Gamification** | XP, streaks, topic completion, quiz history, analytics dashboard |

---

## 🏗️ Architecture

```text
                         ┌──────────────────────────┐
   Next.js (Vercel)  ──► │  FastAPI (Railway)        │
   - Landing/Auth        │  - /chat/stream (SSE)     │
   - Dashboard (XP)      │  - /auth, /progress       │
   - Streaming chat      │  - HITL approve           │
                         └────────────┬─────────────┘
                                      │
                          ┌───────────▼────────────┐
                          │   LangGraph StateGraph  │
                          │                         │
                          │   planner → supervisor  │
                          │        │                │
                          │   ┌────▼─────┐  tools    │
                          │   │specialist│◄────────► │ web_search, youtube,
                          │   │ agents   │  ToolNode │ roadmap, quiz, resume,
                          │   └────┬─────┘           │ interview, dsa, notes,
                          │   analysis → memory      │ resources, analytics
                          │        │                │
                          │     response            │
                          └───────────┬─────────────┘
                                      │
                          ┌───────────▼────────────┐
                          │ Supabase / Postgres     │
                          │ - auth.users            │
                          │ - learner profiles      │
                          │ - checkpoints (LangGraph)│
                          └─────────────────────────┘
```

Full design: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 📁 Repository layout

```text
simple-chatbot/
├── backend/                 # FastAPI + LangGraph multi-agent service
│   ├── app/
│   │   ├── agents/          # graph, supervisor, planner, specialists, model factory
│   │   ├── tools/           # 10 agent tools
│   │   ├── memory/          # checkpointer + long-term Supabase store
│   │   ├── api/             # FastAPI routes (chat/auth/progress)
│   │   ├── config.py        # settings
│   │   └── main.py          # app entrypoint
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── railway.json
│   └── .env.example
├── frontend/                # Next.js (App Router) + Tailwind
│   ├── app/                 # landing, login, signup, dashboard, chat
│   ├── components/
│   ├── lib/
│   ├── vercel.json
│   └── .env.local.example
├── supabase/
│   └── schema.sql           # tables, RLS policies, functions
└── docs/
    └── ARCHITECTURE.md
```

---

## 🚀 Quick start (local)

### Prerequisites
- Python 3.11+, Node.js 20+
- A Supabase project, an OpenAI API key (GPT-5), optionally Tavily + YouTube API keys + LangSmith.

### 1. Database
Run [`supabase/schema.sql`](supabase/schema.sql) in the Supabase SQL editor.

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in keys
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in keys
npm run dev                         # http://localhost:3000
```

---

## ☁️ Deployment
- **Backend → Railway**: `backend/railway.json` + `Dockerfile`.
- **Frontend → Vercel**: `frontend/vercel.json`.
- **Database → Supabase**: `supabase/schema.sql`.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for environment variables and deployment notes.

---

## 🧭 Development milestones
This project was built in professional milestones (see git history / releases): foundation → auth → AI chat → LangGraph migration → tool calling → DSA/Quiz/Roadmap agents → long-term memory → multi-agent supervisor → resume/interview agents → analytics → persistence → observability → deployment → polish.

## 📄 License
MIT
