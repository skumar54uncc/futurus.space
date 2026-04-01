"""
SECURITY: Rate limiting for API endpoints (SlowAPI + Redis).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

from core.config import settings


def _build_storage_uri() -> str:
    """
    SlowAPI storage: Redis when redis_url is set (shared across DO instances).
    rate_limit_storage_uri overrides (memory:// for single-instance dev).
    """
    raw = (settings.rate_limit_storage_uri or "").strip().lower()
    if raw in ("memory", "memory://"):
        return "memory://"
    stripped = (settings.rate_limit_storage_uri or "").strip()
    if stripped:
        return stripped
    ru = (settings.redis_url or "").strip()
    if ru.startswith(("redis://", "rediss://")):
        return ru
    return "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_build_storage_uri(),
    default_limits=["200/minute"],
    headers_enabled=True,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    retry_after = getattr(exc, "retry_after", None)
    headers: dict[str, str] = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down.",
            "retry_after": str(retry_after) if retry_after is not None else None,
        },
        headers=headers,
    )


# SECURITY: Per-route cost tiers (LLM / PDF heavy routes stricter)
LIMITS = {
    "simulation_create": "2/day",
    "analyze_idea": "20/minute",
    "refine_idea": "20/minute",
    "generate_personas": "15/minute",
    "chat": "30/minute",
    "pdf_export": "5/minute",
    "default_authenticated": "100/minute",
    "public": "60/minute",
}
