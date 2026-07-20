# Futurus — Manual steps (Cloud Run + cost cutover)

Do not put real API keys in this file or in `.env.example`. Secrets go only in gitignored `.env` / Cloud Run env / Secret Manager.

---

## 0. Stop DigitalOcean bills (do this first)

1. Open [DigitalOcean Control Panel](https://cloud.digitalocean.com/).
2. **Apps** → open `futurus-api` (or your App Platform app) → **Settings** → **Destroy App**. Confirm.
3. **Databases** → destroy any DO-managed Postgres you no longer use (Futurus DB should already be on **Supabase** — do not delete Supabase).
4. **Redis / Valkey** → destroy any DO-managed Redis if unused (Futurus Redis should be **Upstash**).
5. **Gradient / GenAI / Model Access** → disable or delete the model access key / inference endpoint so it cannot bill.
6. **Droplets / Volumes / Load Balancers** → destroy anything left from experiments.
7. **Billing** → confirm next invoice forecast drops; remove payment method only after $0 forecast if you want.
8. **Vercel** → ensure `NEXT_PUBLIC_BACKEND_URL` points at Cloud Run (`https://futurus-api-….run.app`), not `*.ondigitalocean.app`.
9. Keep `.do/app.yaml` in git as **deprecated rollback reference** only — do not redeploy it.

---

## 1. Fireworks (LLM spend)

1. [Fireworks](https://fireworks.ai) → create/rotate API key (if an old key was ever in `.env.example`, revoke it).
2. Set a **$5/month** budget / spend cap before traffic.
3. Cloud Run env:
   - `FIREWORKS_API_KEY`
   - `FIREWORKS_BASE_URL=https://api.fireworks.ai/inference/v1`
   - `FIREWORKS_MODEL=accounts/fireworks/models/deepseek-v4-flash`
4. Optional free fallback: `GROQ_API_KEYS` (check Groq console: free limits are **per org**, not per key).

---

## 2. Cloud Run (hosting) — already deployed checklist

Project: `futurus-503020` · Region: `us-east1` · Service: `futurus-api`

### Critical: keep CPU allocated during background sims

Inline simulations run in a **background thread**. If CPU is throttled after the HTTP request ends, sims crawl or look “failed”.

```bat
gcloud run services update futurus-api --region=us-east1 --no-cpu-throttling --cpu-boost
```

### Env vars that must be set

See `deploy/cloudrun.env.template`. At minimum:

- `DATABASE_URL`, `REDIS_URL`, `CLERK_SECRET_KEY`, `CLERK_JWT_AUDIENCE`
- `FIREWORKS_API_KEY`, `ENVIRONMENT=production`
- `FUTURUS_SIMULATION_WORKER_INLINE=true`
- `BACKEND_URL=https://futurus-api-543209644263.us-east1.run.app` (your real URL)
- `CORS_EXTRA_ORIGINS=` your Vercel origin(s)

### Redeploy after code changes

```bat
cd /d d:\futurus.space\backend
gcloud builds submit --tag us-east1-docker.pkg.dev/futurus-503020/futurus/futurus-api:latest .
gcloud run deploy futurus-api --image=us-east1-docker.pkg.dev/futurus-503020/futurus/futurus-api:latest --region=us-east1 --platform=managed
```

---

## 3. TimesFM (HF Space) — make statistical validation real

Without this, reports fall back to **heuristic** TimesFM.

1. Confirm your Hugging Face TimesFM Space is running (`backend-timesfm`).
2. Set on Cloud Run:
   - `TIMESFM_SERVICE_URL=https://YOUR_HF_USERNAME-timesfm-service.hf.space`
3. Optional: ping `/health` on that Space; cold starts after ~15 min idle are normal.
4. Verify via admin: `GET /api/admin/llm-status` → `validators.timesfm_remote` should be `true`.
5. After a sim, open the report’s viability / statistical validation — method should be remote TimesFM, not only `heuristic`.

---

## 4. MIRAI / MIRAI-lite — macro context

Two layers exist in code:

| Layer | When it runs | Needs |
|-------|----------------|-------|
| **MIRAI-lite** (`mirai_lite.py`) | Seed build / daily context | Optional `TAVILY_API_KEY` for live search; else default shocks |
| **MIRAI validation** (`mirai_integration.py`) | Report generation | Vendored MIRAI if present; else simulated/heuristic macro |

On Cloud Run (no Celery beat), daily refresh does **not** run automatically. Options:

1. Set `TAVILY_API_KEY` on Cloud Run so seed-time MIRAI-lite can search.
2. Or accept default macro shocks (still produces macro fields on the report).
3. Optional: cron-job.org `GET` your API health only for keep-warm — **not** monitoring; do not treat failures as outages.

Verify: completed report → `viability_summary.macro_validation` / `macro_context` present.

---

## 5. Sentry (optional)

1. Create a Sentry project → copy DSN.
2. Set `SENTRY_DSN` on Cloud Run.
3. Trigger a test error or watch a failed sim — event should appear scrubbed of auth headers.

---

## 6. Final verification checklist

- [ ] `curl https://YOUR.run.app/health` → `api/database/redis` all `ok`
- [ ] DigitalOcean App Platform app **destroyed**; no DO Gradient key in use
- [ ] Vercel `NEXT_PUBLIC_BACKEND_URL` = Cloud Run URL
- [ ] One full simulation completes end-to-end
- [ ] Cloud Run logs show `fireworks_deepseek` / `groq_*` — **no** `digitalocean_*`
- [ ] `/api/admin/llm-status` shows Fireworks primary + usage snapshot
- [ ] `TIMESFM_SERVICE_URL` set and report statistical validation enabled (or you knowingly accept heuristic)
- [ ] Fireworks $5 cap + GCP $1 budget alert

---

## 7. Oracle account

Leave the Free Tier account idle. Do not keep retrying A1 unless you want a free VM later. No need to delete the account.
