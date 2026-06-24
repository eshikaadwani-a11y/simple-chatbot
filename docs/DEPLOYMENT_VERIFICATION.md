# Deployment Verification

A step-by-step, copy-paste checklist to take LearnGraph from repo → live, with an
**acceptance criterion** for every step. Tick each box; if one fails, stop and fix
before continuing.

> Companion to `DEPLOYMENT_AUDIT.md` (risks/rationale). This file is the runbook.

---

## Phase 0 — Local verification (before any cloud)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check app tests           # ✅ "All checks passed!"
ruff format --check app tests  # ✅ "… already formatted"
pytest --cov=app --cov-fail-under=70   # ✅ green, coverage ≥ 70%
uvicorn app.main:app --port 8000       # ✅ logs "Multi-agent graph compiled"
curl localhost:8000/health             # ✅ {"status":"ok",...}

# Frontend
cd ../frontend
npm install                    # ✅ generates package-lock.json — COMMIT IT
npm run lint                   # ✅ no errors
npx tsc --noEmit               # ✅ no type errors
npm test                       # ✅ vitest passes
npm run build                  # ✅ build succeeds
```

- [ ] All backend checks pass locally.
- [ ] `frontend/package-lock.json` generated and committed.
- [ ] `npm run build` succeeds.

> Fixes already applied for the build: tests + `vitest.config.ts` are excluded from
> the Next type-check; the coverage gate omits infra modules (DB/bootstrapping) so
> 70% reflects application logic.

---

## Phase 1 — Supabase

1. Create a project. Note the **Project URL**, **anon key**, **service-role key**,
   and **JWT secret** (Settings → API), and the **pooler** `DATABASE_URL`
   (Settings → Database → Connection pooling).
2. In the SQL editor, run **`supabase/schema.sql`** (tables, RLS, triggers).
   - The RAG table needs the vector extension; the schema runs
     `create extension if not exists vector;`. If your plan lacks it, see `docs/RAG.md`.
3. Auth → URL config: set Site URL + redirect URLs to your Vercel domain.

- [ ] `schema.sql` applied with no errors.
- [ ] `select * from learner_profiles;` returns 0 rows without error (table + RLS exist).
- [ ] Copied URL, anon key, service-role key, JWT secret, pooler `DATABASE_URL`.

---

## Phase 2 — Backend on Railway

1. New project → Deploy from repo (root = `backend/`, Dockerfile builder via
   `railway.json`).
2. Set env vars (see `.env.example`). Minimum to boot in production:
   `OPENAI_API_KEY`, `LEARNGRAPH_DEFAULT_MODEL`, `SUPABASE_URL`,
   `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL`,
   `ENVIRONMENT=production`, `CORS_ORIGINS=<your-vercel-url>`.
3. Deploy. Watch logs.

- [ ] Logs show **"Async Postgres checkpointer ready."** (not the in-memory warning).
- [ ] `GET https://<backend>/health` → 200.
- [ ] `GET https://<backend>/meta/models` → lists `gpt-5` and your default.
- [ ] Start with **1 instance** (in-process rate limiting; see audit).

> If you see "Postgres checkpointer init failed … falling back to in-memory", the
> `DATABASE_URL` is wrong/unreachable — fix it; HITL resume won't survive restarts on
> the in-memory fallback.

---

## Phase 3 — Ingest the knowledge base (RAG)

With the backend env available (locally or via Railway shell):

```bash
cd backend
python -m app.rag.ingest    # embeds docs/knowledge into the vector store
```

- [ ] Ingest reports the number of chunks embedded.
- [ ] `select count(*) from knowledge_documents;` > 0 (when using pgvector).

> Without `OPENAI_API_KEY`/DB the system uses a deterministic in-memory fallback so
> the feature still works in dev — but production retrieval quality needs real
> embeddings + pgvector. See `docs/RAG.md`.

---

## Phase 4 — Frontend on Vercel

1. Import repo, set root to `frontend/`.
2. Env vars (Production + Preview): `NEXT_PUBLIC_SUPABASE_URL`,
   `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_BASE_URL=https://<backend>`.
   (Optional `NEXT_PUBLIC_ADMIN_EMAILS` to show the admin link.)
3. Deploy.

- [ ] Build succeeds on Vercel.
- [ ] Landing page renders at the Vercel URL.

---

## Phase 5 — Connect & smoke test

1. Add the Vercel URL to backend `CORS_ORIGINS` (comma-separated, no trailing
   slash); redeploy backend.

- [ ] **Sign up / log in** works (Supabase email confirm if enabled).
- [ ] **Chat streams** token-by-token (open DevTools → Network → the `/chat/stream`
      response should arrive incrementally, not in one chunk).
- [ ] **Roadmap** request triggers the **Approve/Reject** prompt; approving persists
      it (check `roadmaps` table).
- [ ] **Resume upload** returns an ATS score.
- [ ] **Dashboard** shows XP/streak after activity.
- [ ] **Admin analytics** (`/admin`, as an admin email) shows usage + cost.

---

## Phase 6 — CI/CD gate

- [ ] Both GitHub Actions workflows are **green** on the PR.
- [ ] Branch protection requires CI to pass before merge (recommended).

---

## Common first-deploy failures (and the fix)

| Symptom | Cause | Fix |
|---|---|---|
| Chat 500s; logs mention sync/async checkpointer | DB checkpointer misconfig | Verify `DATABASE_URL` (pooler); confirm "Async … ready" log |
| Every LLM call 400s | GPT-5 model id or unsupported param | Confirm model id; temperature override already removed |
| CORS error in browser | Vercel URL not in `CORS_ORIGINS` | Add it, redeploy backend |
| Chat arrives all-at-once | Proxy buffering | Anti-buffering headers are set; confirm no extra proxy buffers SSE |
| App won't boot in prod | Missing required env | `ENVIRONMENT=production` enforces it — set all required vars |
| Vercel build fails on test types | tests in type-check path | Already excluded in `tsconfig.json` |
| Coverage gate red | Untested infra counted | Already omitted in `pyproject.toml`; add tests if app logic dips |

---

## Done = all boxes ticked
When every box above is checked, you have a **verified, reproducible deployment** —
the single biggest jump in this project's perceived quality.
