# Changelog

All notable changes are grouped by development milestone.

## v1.0.0 — Production-ready AI learning platform
- Error handling across tools and graph nodes (tools never crash the agent loop).
- Loading states and live agent/tool indicators in the chat UI.
- Mobile-responsive layouts (Tailwind).
- Security: JWT validation on protected routes, Supabase RLS, backend-only service role key.
- Documentation: README + `docs/ARCHITECTURE.md`.

### Milestones
1. Project foundation (Next.js + FastAPI + Supabase + structure)
2. Authentication & session management
3. GPT-5 model layer + streaming chat UI
4. LangGraph agent workflow (StateGraph, planner, supervisor, tool node, routing)
5. Dynamic tool-calling framework (search, notes, resources, youtube)
6. DSA mentor tool
7. Adaptive quiz generation
8. Personalized roadmap generator
9. Long-term memory & learner profiles
10. Supervisor-based multi-agent orchestration
11. Resume review agent
12. Interview coach agent
13. Analytics dashboard (XP, streaks, charts)
14. State persistence & workflow recovery (checkpointing)
15. LangSmith observability
16. Deployment (Railway + Vercel + Supabase)
17. Polish release
