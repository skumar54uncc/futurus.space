# Deploying Futurus to Production (Free Stack)

## Step 1 — Supabase (Database)

1. Go to [supabase.com](https://supabase.com) and create a new project (free tier)
2. Go to Settings -> Database -> Connection string -> URI
3. Copy the connection URI (format: `postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres`)
4. Convert to async format: `postgresql+asyncpg://postgres:[password]@db.[project].supabase.co:5432/postgres`
5. Save as `DATABASE_URL` environment variable

## Step 2 — Upstash (Redis)

1. Go to [upstash.com](https://upstash.com) and create a Redis database (free tier)
2. Copy the `REDIS_URL` (starts with `rediss://`)
3. Save as `REDIS_URL` environment variable

## Step 3 — Clerk (Authentication)

1. Go to [clerk.com](https://clerk.com) and create an application (free tier, 10k MAU)
2. Copy `CLERK_SECRET_KEY` and `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
3. In Clerk dashboard, add `futurus.dev` to allowed domains
4. Set redirect URLs:
   - Sign-in: `/sign-in`
   - Sign-up: `/sign-up`
   - After sign-in: `/dashboard`
   - After sign-up: `/new`

## Step 4 — Railway (Backend + Worker)

1. Go to [railway.app](https://railway.app) and create a new project
2. Connect your GitHub repo
3. Create first service (API):
   - Root directory: `/backend`
   - Dockerfile: `Dockerfile.prod`
   - Add environment variables: `DATABASE_URL`, `REDIS_URL`, `CLERK_SECRET_KEY`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_TIER1`, `LLM_MODEL_TIER2`, `ZEP_API_KEY`
   - Add custom domain: `api.futurus.dev`
4. Create second service (Celery worker):
   - Root directory: `/backend`
   - Dockerfile: `Dockerfile.worker`
   - Same environment variables as API service

## Step 5 — Vercel (Frontend)

1. Go to [vercel.com](https://vercel.com) and import your GitHub repo
2. Set root directory to `/frontend`
3. Add environment variables:
   - `NEXT_PUBLIC_BACKEND_URL` = `https://api.futurus.dev`
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` = your Clerk publishable key
4. Add custom domain: `futurus.dev`
5. Deploy — automatic on every git push

## Step 6 — DNS (at your domain registrar)

Add these DNS records where futurus.dev is registered:

| Type | Name | Value |
|------|------|-------|
| CNAME | @ | cname.vercel-dns.com |
| CNAME | www | cname.vercel-dns.com |
| CNAME | api | [railway-app].railway.app |

## Step 7 — Run Migrations

```bash
railway run alembic upgrade head
```

Or connect to Supabase SQL editor and run the migrations manually.

## Done

`futurus.dev` is live. Monthly cost: $0.
