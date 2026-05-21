from redis.asyncio import Redis

from src.core.config import settings

redis_client = Redis.from_url(
    settings.redis_url,
)


async def ping_redis():
    return await redis_client.ping()
