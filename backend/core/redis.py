"""
Shared asyncio Redis pool for FastAPI (WebSocket pub/sub, health, idempotency).
Capped connections for Upstash TCP limits.

Optional Upstash REST client (HTTP, stateless) for distributed LLM counters — no extra TCP slots.
"""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Optional

import redis.asyncio as aioredis

from core.config import settings

if TYPE_CHECKING:
    from upstash_redis import Redis as UpstashRedisType

try:
    from upstash_redis import Redis as UpstashRedis
except ImportError:
    UpstashRedis = None  # type: ignore[misc, assignment]

redis_pool = aioredis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=settings.redis_max_connections,
    decode_responses=True,
)


async def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    await redis_pool.disconnect()


@lru_cache(maxsize=1)
def _upstash_redis_cached() -> Optional["UpstashRedisType"]:
    if UpstashRedis is None:
        return None
    url = (settings.upstash_redis_rest_url or "").strip()
    token = (settings.upstash_redis_rest_token or "").strip()
    if not url or not token:
        return None
    return UpstashRedis(url=url, token=token)


def get_upstash_redis_optional() -> Optional["UpstashRedisType"]:
    """REST client when UPSTASH_* env is set; otherwise None."""
    return _upstash_redis_cached()


def get_upstash_redis() -> "UpstashRedisType":
    """Strict accessor for scripts / callers that require Upstash."""
    r = get_upstash_redis_optional()
    if r is None:
        raise RuntimeError(
            "UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set. "
            "Get them from console.upstash.com"
        )
    return r


def clear_upstash_client_cache() -> None:
    _upstash_redis_cached.cache_clear()
