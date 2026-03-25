"""
SECURITY: Rate limiting for API endpoints (SlowAPI + Redis).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

from core.config import settings

# SECURITY: Distributed limits via Redis for multi-worker / Railway deploys
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=["200/minute"],
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    # SECURITY: Generic client message; do not leak internal limit config
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please slow down.",
            "retry_after": getattr(exc, "retry_after", None),
        },
    )


# SECURITY: Per-route cost tiers (LLM / PDF heavy routes stricter)
LIMITS = {
    "simulation_create": "10/minute",
    "analyze_idea": "20/minute",
    "refine_idea": "20/minute",
    "generate_personas": "15/minute",
    "chat": "30/minute",
    "pdf_export": "5/minute",
    "default_authenticated": "100/minute",
    "public": "60/minute",
}
