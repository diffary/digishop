from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from app.core.config import get_settings

_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _client


async def get_redis() -> AsyncIterator[aioredis.Redis]:
    yield get_redis_client()
