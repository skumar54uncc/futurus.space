# Deploy Futurus API on DigitalOcean

Frontend (Next.js) should stay on **Vercel** (root directory `frontend/`). This guide covers the **FastAPI backend** (`backend/`), **Managed PostgreSQL**, **Managed Redis**, and **DigitalOcean Gradient** inference.

## 1. Prerequisites

- GitHub repo connected to DigitalOcean.
- **Model access key**: Agent Platform → Model access keys → create key (note the secret once).
- List model IDs:  
  `curl -s https://inference.do-ai.run/v1/models -H "Authorization: Bearer YOUR_KEY"`

Set `LLM_MODEL_TIER1` and `LLM_MODEL_TIER2` to exact `id` values from that response.

## 2. Managed PostgreSQL

1. **Databases → PostgreSQL** → same region as your app (e.g. NYC3).
2. **Trusted sources**: allow your App Platform app (or restrict to VPC).
3. Connection string: convert to **`postgresql+asyncpg://`** (replace `postgresql://` or `postgres://` prefix). Keep SSL query params per DO docs.

## 3. Managed Redis

1. **Databases → Redis** (or Valkey) → same region.
2. Trusted sources: same as Postgres.
3. Copy `REDIS_URL` (`redis://` or `rediss://`).

## 4. App Platform (Web Service)

1. **Create → App Platform → GitHub** → select repo and branch.
2. **Resource**: Web Service.
3. **Source directory**: `backend`
4. **Dockerfile path**: `Dockerfile` (file in this folder).
5. **HTTP port**: `8080` (or match `PORT` your platform injects; Dockerfile defaults to `8080`).
6. **Instance**: start small; scale up if simulations OOM.

### Environment variables (encrypt secrets)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `REDIS_URL` | From managed Redis |
| `CLERK_SECRET_KEY` | Clerk secret |
| `CLERK_JWT_AUDIENCE` | Required when `ENVIRONMENT=production` |
| `ZEP_API_KEY` | Zep |
| `MODEL_ACCESS_KEY` | DigitalOcean model access key |
| `LLM_BASE_URL` | `https://inference.do-ai.run/v1` |
| `LLM_API_KEY` | Same value as `MODEL_ACCESS_KEY` (chat + consistency) |
| `LLM_MODEL_TIER1` | DO model id (quality) |
| `LLM_MODEL_TIER2` | DO model id (volume / cheaper) |
| `ENVIRONMENT` | `production` |
| `BACKEND_URL` | Public URL of this app, e.g. `https://your-app.ondigitalocean.app` |
| `APP_DOMAIN` | Your Vercel or custom frontend hostname |
| `FUTURUS_SIMULATION_WORKER_INLINE` | `true` (unless you run Celery separately) |
| `MAX_COST_PER_SIMULATION_USD` | e.g. `5`–`10` |
| `CORS_EXTRA_ORIGINS` | Optional comma list, e.g. `https://custom-domain.com` |
| `AWS_*` | Optional, for S3 PDF presigning |

Redeploy after changing variables.

## 5. Vercel (frontend)

- Root directory: **`frontend`**
- `NEXT_PUBLIC_BACKEND_URL` = App Platform HTTPS URL (no trailing slash)
- Clerk `NEXT_PUBLIC_*` variables per `frontend/.env.production.example`

## 6. Clerk

- Add your Vercel URL(s) to Clerk allowed domains.
- `CLERK_JWT_AUDIENCE` must match production Frontend API settings.

## 7. Optional: App spec

See `.do/app.yaml` in the repo root for a template **App Platform spec** (replace placeholders before use).
