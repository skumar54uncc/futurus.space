# Futurus Free Production Stack

| Service | Provider | Free Tier | Cost |
|---------|----------|-----------|------|
| Frontend hosting | Vercel | Unlimited deploys | FREE |
| Backend hosting | Railway | $5/mo credit | FREE |
| PostgreSQL database | Supabase | 500MB | FREE |
| Redis / job queue | Upstash | 10k cmd/day | FREE |
| Authentication | Clerk | 10,000 MAU | FREE |
| File storage | Cloudflare R2 | 10GB | FREE |
| Domain | futurus.dev | Already purchased | $13/yr |
| SSL certificates | Auto (Vercel/Railway) | Included | FREE |
| Analytics | Vercel Analytics | Basic | FREE |

**Total monthly cost: $0**
**Total annual cost: $13** (just the domain)

## Service Details

### Vercel (Frontend)
- Unlimited deployments from GitHub
- Auto-preview for PRs
- Edge network CDN
- Custom domain with auto-SSL

### Railway (Backend + Worker)
- $5 free credit per month (enough for low-traffic MVP)
- Deploy from Dockerfile
- Auto-restart on failure
- Environment variable management

### Supabase (PostgreSQL)
- 500MB database storage
- 2 projects on free tier
- Connection pooling included
- Dashboard for DB management

### Upstash (Redis)
- 10,000 commands/day free
- 256MB storage
- REST API + native Redis protocol
- Serverless (no idle cost)

### Clerk (Authentication)
- 10,000 monthly active users free
- Social logins (Google, GitHub, etc.)
- Email/password auth
- User management dashboard
