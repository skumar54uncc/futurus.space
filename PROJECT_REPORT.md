# Futurus — Project Report (clone + interviews)

**Last updated:** 2026-07-20  
**Repo:** https://github.com/skumar54uncc/futurus.space  
**Live API:** https://futurus-api-543209644263.us-east1.run.app  
**Product domain:** futurus.dev  

This is the single source of truth for what the project is, how it is hosted, what was fixed recently, and how to talk about it in interviews. Ops cutover steps live in [`MANUAL_STEPS.md`](./MANUAL_STEPS.md).

---

## 1. One-liner

Futurus is an AI idea simulator: founders describe a product in plain English; a multi-agent market simulation stress-tests adoption, churn, and referrals; a structured report returns viability, risks, pivots, and optional industry citations.

---

## 2. Stack (what actually runs today)

| Layer | Choice | Notes |
|--------|--------|--------|
| Frontend | Next.js 14 (App Router) on **Vercel** | Clerk auth, wizard → live sim → report |
| Backend | FastAPI + Uvicorn on **Google Cloud Run** | Service `futurus-api`, project `futurus-503020`, region `us-east1` |
| Database | **Supabase** Postgres | SQLAlchemy async + asyncpg; Alembic migrations |
| Redis | **Upstash** | Progress pub/sub, WebSockets, rate limits / counters |
| Auth | **Clerk** | JWT validated in FastAPI; frontend Clerk middleware |
| Primary LLM | **Fireworks** DeepSeek V4 Flash | OpenAI-compatible API |
| Fallback LLM | **Groq** (`GROQ_API_KEYS` or `GROQ_API_KEY`) | Optional Gemini / OpenRouter if keyed |
| TimesFM | Remote **Hugging Face Space** | `TIMESFM_SERVICE_URL`; else heuristic validation |
| Macro context | MIRAI-lite | Optional `TAVILY_API_KEY`; else defaults |
| Object storage / email | AWS S3 / SES (optional) | Report PDFs, notify-on-complete |

**Not the current host:** DigitalOcean App Platform / Gradient (deprecated), Railway, Oracle Always Free (abandoned after A1 capacity errors).

---

## 3. Architecture map (request → report)

```
Browser (Vercel)
  → Clerk session
  → FastAPI (Cloud Run)
       → create Simulation (QUEUED)
       → inline daemon thread OR Celery worker
            BUILDING_SEED → GENERATING_PERSONAS → RUNNING → GENERATING_REPORT
       → Redis publish progress → WebSocket to UI
       → Report row (metrics + narrative + validation)
  → Report page + Ask analyst chat
```

### Important paths

| Concern | Path |
|---------|------|
| API entry | `backend/main.py` |
| Create / list sims | `backend/api/routes/simulations.py` |
| Worker lifecycle | `backend/workers/simulation_worker.py` |
| LLM router | `backend/services/llm_router.py` |
| Report build | `backend/services/report_generator.py` |
| Lease recovery | `backend/services/simulation_recovery.py` |
| TimesFM client | `backend/services/timesfm_client.py` |
| Simulation adapter | `backend/simulation_engine/mirofish_adapter.py` |
| Frontend report | `frontend/app/(dashboard)/simulation/[id]/report/page.tsx` |
| Section fallbacks | `frontend/lib/reportSectionFallbacks.ts` |
| Cloud Run env template | `deploy/cloudrun.env.template` |

---

## 4. Simulation pipeline (interview-depth)

1. **Wizard** — analyze/refine idea, generate personas (`idea_analyzer`, `persona_generator`).
2. **Create** — credit/plan limits → insert sim → start worker (`FUTURUS_SIMULATION_WORKER_INLINE=true` on Cloud Run).
3. **Seed** — MIRAI-lite macro context (`seed_builder`).
4. **Personas** — segment agents for the run.
5. **Turns** — `MiroFishAdapter` drives agent events; if MiroFish package is absent, **archetype-collapse mock** (one LLM call per segment archetype) still produces a full event stream.
6. **Heartbeat** — each turn updates `simulations.last_heartbeat_at` so another instance’s cold start does not falsely mark a healthy run `FAILED` (25‑minute lease).
7. **Report** — metrics → TimesFM + MIRAI validation → Tavily citations (optional) → narrative LLM.
8. **Fallback** — if narrative LLM fails: metrics-based “Will it work?”, plus heuristic failure timeline / risks / pivots / insights (`narrative_source: heuristic`). Empty sections are also filled on **API read** and in the **UI** so older broken rows still render.

Statuses: `queued` → `building_seed` → `generating_personas` → `running` → `generating_report` → `completed` | `failed`.

---

## 5. Recent reliability work (master, Jul 2026)

| Commit | What |
|--------|------|
| `a41b3df` | Narrative heuristic on LLM failure; heartbeat lease recovery; remove unused `ensemble_runner.py`; quiet report UX |
| `d850c0f` | Never leave risk/timeline/pivots/insights empty when narrative LLM fails |
| `2b3c5ae` | Fill empty sections on report GET + frontend so **existing** reports show sections again |

Also on master earlier: Fireworks + Cloud Run cutover, per-sim `llm_usage` cost persistence, softer cold-start recovery, CI path fixes.

**Live revision after these fixes:** Cloud Run `futurus-api` (redeployed through `00011+`). Health must show `api` / `database` / `redis` = `ok`.

---

## 6. After you clone this repo

```bat
git clone https://github.com/skumar54uncc/futurus.space.git
cd futurus.space
```

1. Copy env templates — **never commit real keys**:
   - Root / backend: `.env.example` → gitignored `.env`
   - Frontend: `frontend/.env.example` → `frontend/.env.local`
   - Cloud Run checklist: `deploy/cloudrun.env.template` + `MANUAL_STEPS.md`
2. Backend: `cd backend && pip install -r requirements.txt`
3. Frontend: `cd frontend && npm ci && npm run dev`
4. Local DB/Redis: `docker-compose.yml` (optional); or point at Supabase + Upstash.
5. Run tests: `cd backend && pytest -q tests/`
6. Production deploy is **manual Cloud Run** (git push ≠ live API):

```bat
cd /d d:\futurus.space\backend
gcloud builds submit --tag us-east1-docker.pkg.dev/futurus-503020/futurus/futurus-api:latest . --project=futurus-503020
gcloud run deploy futurus-api --image=us-east1-docker.pkg.dev/futurus-503020/futurus/futurus-api:latest --region=us-east1 --platform=managed --project=futurus-503020 --no-cpu-throttling --cpu-boost
```

Required production env (names only): `DATABASE_URL`, `REDIS_URL`, `CLERK_SECRET_KEY`, `CLERK_JWT_AUDIENCE`, `FIREWORKS_API_KEY`, `GROQ_API_KEYS` (or `GROQ_API_KEY`), `ENVIRONMENT=production`, `FUTURUS_SIMULATION_WORKER_INLINE=true`, `BACKEND_URL`, `CORS_EXTRA_ORIGINS`, optional `TIMESFM_SERVICE_URL`, `TAVILY_API_KEY`, `ADMIN_EMAIL`.

Frontend: `NEXT_PUBLIC_BACKEND_URL` → Cloud Run URL; Clerk publishable keys.

---

## 7. Honest interview talking points

**Lead with:** end-to-end product (wizard → multi-agent sim → report), multi-provider LLM router with cost metering, and reliability engineering so reports never blank out.

**Say clearly:**

- **Inline Cloud Run workers** are good enough for a portfolio demo; long sims on scale-to-zero can still die with the instance. Heartbeats fix *false* FAILED from other cold starts — they do not make the run immortal. Upgrade path: Cloud Tasks, `min-instances`, or a dedicated worker.
- **MiroFish** may run as a full engine when mounted; otherwise the adapter’s archetype mock still completes sims (speed/cost tradeoff).
- **TimesFM / MIRAI** are soft validators: remote HF when configured, else heuristics. Do not claim local `vendors/` clones — that was old, inaccurate docs (removed).
- **Billing:** Stripe paths live under `archive/billing/`; live product uses plan/credit limits, not a full Stripe checkout unless restored.
- **Cost discipline:** Fireworks primary + Groq fallback, token metering on `simulations.llm_usage`, Fireworks spend cap + GCP budget alerts.

**Sample answer (60s):**  
“I built Futurus, a multi-agent idea simulator. Next.js on Vercel talks to FastAPI on Cloud Run with Clerk, Supabase, and Upstash. Sims run inline today with heartbeat-based lease recovery so cold starts don’t falsely fail healthy runs. Inference is Fireworks DeepSeek with Groq fallback and per-run cost tracking. When the report LLM fails, we degrade to metrics-based narrative and risk sections so founders still get a usable report instead of empty UI.”

---

## 8. Docs in this repo (after cleanup)

| File | Role |
|------|------|
| **`PROJECT_REPORT.md`** (this file) | Clone + interview brief |
| **`README.md`** | Short pointer into the project |
| **`MANUAL_STEPS.md`** | Live ops: Fireworks, Cloud Run, DO teardown, verification |
| **`archive/billing/README.md`** | How archived Stripe modules could be restored |
| **`deploy/cloudrun.env.template`** | Env names for Cloud Run |

**Deleted as outdated / wrong (Jul 2026):** Railway/DO-centric `docs/DEPLOY.md`, `docs/FREE_STACK.md`, `docs/DNS_SETUP.md`, `deploy/digitalocean.md`, and inaccurate TimesFM/MIRAI “vendors cloned” docs (`INTEGRATION_*`, `README_INTEGRATION.md`, `DEPLOYMENT_CHECKLIST.md`).

---

## 9. Status snapshot (2026-07-20)

- **GitHub `master`:** up to date with reliability + report-section fixes (`2b3c5ae` and predecessors).
- **Cloud Run:** healthy (`api` / `database` / `redis` ok) after redeploys through revision `futurus-api-00011-dp9`+.
- **Frontend:** deploys from Vercel on `master` when the project is linked.
- **Still manual for you:** keep Fireworks key rotated / spend-capped; confirm DigitalOcean billing is $0 if you destroyed DO apps; optional TimesFM Space URL and Tavily for richer validation.
