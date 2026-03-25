import redis.asyncio as aioredis
from core.config import settings

redis_pool = aioredis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=20,
    decode_responses=True,
)


async def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=redis_pool)


async def close_redis():
    await redis_pool.disconnect()
