# Deployment Readiness Audit

You said you'll deploy tomorrow. Here's exactly what to set, what will bite you,
and the order to do it in. **Status legend:** ✅ ready · ⚠️ needs action · ❌ blocker.

> Reality check: this project has **not been built or deployed yet** in any
> environment. Treat the first CI run and first deploy as the real test. The known
> code-level blockers from the audit are fixed; the remaining risks are
> environmental and version-related.

---

## 0. Pre-flight (do this first)

1. **Push the branch and let CI run.** This is the first real `pip install`,
   `npm install`, `pytest`, and `next build`. Fix whatever it surfaces before
   deploying. ⚠️
2. **Confirm the GPT-5 model id** in `backend/app/agents/models.yaml` matches a
   model enabled on your OpenAI account (else 404/400 at runtime). ⚠️
3. **Generate a frontend lockfile**: run `npm install` once and commit
   `frontend/package-lock.json` for reproducible Vercel/CI builds. ⚠️

---

## 1. Environment variables

### Backend (Railway) — from `backend/.env.example`
| Var | Required? | Notes |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | Or another provider key matching `LEARNGRAPH_DEFAULT_MODEL` |
| `LEARNGRAPH_DEFAULT_MODEL` | ✅ | `gpt-5` (verify availability) |
| `SUPABASE_URL` | ✅ | Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | **Backend only** — never expose |
| `SUPABASE_JWT_SECRET` | ✅ | Settings → API → JWT Secret; without it the API runs in **dev mode (no real auth)** |
| `DATABASE_URL` | ✅ | Use the Supabase **pooler** URI; required for durable memory + HITL across restarts |
| `ENVIRONMENT` | ✅ | Set to `production` so env validation fails fast on missing config |
| `CORS_ORIGINS` | ✅ | Your exact Vercel URL(s), comma-separated (no trailing slash) |
| `TAVILY_API_KEY` | ⚠️ optional | Without it web_search returns no live results |
| `YOUTUBE_API_KEY` | ⚠️ optional | Without it youtube tool returns a search link only |
| `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` | ⚠️ optional | Enable LangSmith |
| `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_HEAVY_PER_MINUTE` | optional | Defaults 60 / 20 |

> **Gotcha:** with `ENVIRONMENT=production`, the app **refuses to boot** if an LLM
> key, Supabase creds, JWT secret, or `DATABASE_URL` is missing. That's intentional
> — set them all or it won't start.

### Frontend (Vercel) — from `frontend/.env.local.example`
| Var | Required? | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | Public |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | Public anon key (not service role) |
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | The Railway backend URL (https) |

---

## 2. Supabase
- ✅ Run `supabase/schema.sql` (tables, RLS, signup + updated_at triggers).
- ⚠️ **Connection string:** use the **pooler** (pgBouncer) URI for `DATABASE_URL`.
  The code sets `prepare_threshold=0`, which is required for pgBouncer transaction
  mode — good. Verify the URI/port from Settings → Database.
- ⚠️ **Checkpoint tables:** created automatically by `AsyncPostgresSaver.setup()` on
  first boot. The DB user must have `CREATE TABLE` rights (the default Postgres role
  does).
- ⚠️ **Auth settings:** configure allowed redirect URLs / site URL to your Vercel
  domain so email confirmation links work.
- ❌→✅ Don't put the service-role key in the frontend (it isn't — verified).

---

## 3. Railway (backend)
- ✅ `Dockerfile` + `railway.json` (Dockerfile builder, `/health` healthcheck,
  restart policy). `$PORT` is honored.
- ⚠️ **Workers/replicas:** HITL resume and rate limiting are correct on a **single
  instance**. With the Postgres checkpointer, multiple instances share agent state
  (good), but the **in-process rate limiter does not** — fine to launch with 1
  instance; add Redis before scaling out.
- ⚠️ **Build time/size:** the image installs torch-free but heavy LLM SDKs; first
  build may be slow. No GPU needed.
- ⚠️ **SSE behind Railway's proxy:** anti-buffering headers are now set; verify a
  real streamed response actually arrives token-by-token after deploy.
- ⚠️ **Startup DB dependency:** if `DATABASE_URL` is unreachable, the app logs an
  error and falls back to in-memory (non-durable). Check logs after first boot to
  confirm "Async Postgres checkpointer ready."

---

## 4. Vercel (frontend)
- ✅ `vercel.json` (Next.js framework preset).
- ⚠️ **Set the 3 `NEXT_PUBLIC_*` env vars** in the Vercel project (Production +
  Preview). Missing ones no longer crash the app (guarded) but auth/API won't work.
- ⚠️ **`NEXT_PUBLIC_API_BASE_URL` must be the deployed Railway URL**, and that URL
  must be in the backend's `CORS_ORIGINS` — the classic first-deploy CORS failure.
- ⚠️ **Lockfile:** commit `package-lock.json` so Vercel installs the versions you
  tested.

---

## 5. Build issues to expect
- ⚠️ `next build` runs type-checking on **all** `.ts` including `vitest.config.ts`
  and `tests/` — those import `vitest`, which is a dev dependency (present in CI/
  Vercel installs). If Vercel prunes dev deps before build, exclude tests from the
  Next build tsconfig or move them out of the type-check path.
- ⚠️ First backend `pip install` is the real compatibility test for the pinned
  langgraph/langchain/checkpoint-postgres versions.

---

## 6. Dependency issues
- ⚠️ `langgraph==0.2.50` + `langgraph-checkpoint-postgres==2.0.7` + `langchain
  0.3.x`: pinned but **not verified to resolve together** in this sandbox (no
  network). CI will confirm. If it fails, bump to a known-good matrix.
- ⚠️ `init_chat_model` provider strings: `openai`/`anthropic`/`google_genai` are
  standard; **`deepseek`** may require a different integration package — only an
  issue if you actually switch to it.
- ✅ `psycopg[binary,pool]` provides the async pool used by the checkpointer.

---

## 7. CI issues
- ⚠️ **Coverage gate (70%)** has never been measured. The first backend CI run may
  fail on coverage even if tests pass. Mitigation: run `pytest --cov` locally and
  either add a couple of tests or adjust `--cov-fail-under`.
- ⚠️ **Frontend CI** runs `next build`; see the tests/tsconfig note above.
- ✅ Workflows are path-filtered and trigger on push + PR.

---

## Deploy-tomorrow checklist (TL;DR)
1. ⬜ Push branch → watch both CI workflows go green (fix coverage/build if red).
2. ⬜ Commit `frontend/package-lock.json`.
3. ⬜ Confirm GPT-5 model id against your OpenAI account.
4. ⬜ Apply `supabase/schema.sql`; grab the pooler `DATABASE_URL` + JWT secret.
5. ⬜ Deploy backend to Railway with all env vars; check logs for "Async Postgres
   checkpointer ready" and hit `/health`.
6. ⬜ Deploy frontend to Vercel with the 3 public env vars pointing at Railway.
7. ⬜ Add the Vercel URL to backend `CORS_ORIGINS`; redeploy backend.
8. ⬜ Smoke test: sign up → send a chat (confirm streaming) → roadmap (confirm HITL
   approve) → upload a resume → check dashboard updates.
9. ⬜ Start with **1 backend instance**; add Redis before scaling out.
