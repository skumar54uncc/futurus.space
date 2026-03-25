# DNS Setup for futurus.dev

## Records to add at your domain registrar

### Frontend (Vercel)

| Type | Name | Value |
|------|------|-------|
| CNAME | @ | cname.vercel-dns.com |
| CNAME | www | cname.vercel-dns.com |

### Backend API (Railway)

| Type | Name | Value |
|------|------|-------|
| CNAME | api | [your-railway-app].railway.app |

Replace `[your-railway-app]` with the actual Railway app hostname from your Railway dashboard.

## Result

- `futurus.dev` — Frontend (Next.js on Vercel)
- `api.futurus.dev` — Backend API (FastAPI on Railway)
- `www.futurus.dev` — Redirects to futurus.dev

## Verification

After adding DNS records, verify propagation:

```bash
# Check frontend
nslookup futurus.dev

# Check API
nslookup api.futurus.dev
```

SSL certificates are provisioned automatically by Vercel and Railway once DNS records propagate (usually 5-30 minutes).
