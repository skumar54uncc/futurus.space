# Futurus

AI idea simulator — multi-agent market stress-test → viability report.

**Live API:** https://futurus-api-543209644263.us-east1.run.app  
**Product:** [futurus.dev](https://futurus.dev)

| Doc | Use when |
|-----|----------|
| **[PROJECT_REPORT.md](./PROJECT_REPORT.md)** | Cloning, architecture, interview prep (start here) |
| **[MANUAL_STEPS.md](./MANUAL_STEPS.md)** | Cloud Run / Fireworks / cutover ops |
| `deploy/cloudrun.env.template` | Production env var names |

### Quick local

```bat
cd backend && pip install -r requirements.txt
cd ..\frontend && npm ci && npm run dev
```

Copy `.env.example` → `.env` (never commit secrets). Backend tests: `cd backend && pytest -q tests/`.

### Hosting (current)

- Frontend → **Vercel**
- API → **Google Cloud Run** (`futurus-api`)
- DB → **Supabase** · Redis → **Upstash** · Auth → **Clerk**
- LLM → **Fireworks** (primary) + **Groq** (fallback)

Git push updates GitHub (and Vercel if connected). **Cloud Run must be redeployed with `gcloud`** — see `MANUAL_STEPS.md`.
