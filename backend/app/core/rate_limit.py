from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status

from app.core.redis import get_redis


def rate_limit(limit: int = 10, window_sec: int = 60):
    async def dependency(
        request: Request,
        redis: Annotated[aioredis.Redis, Depends(get_redis)],
    ) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{request.url.path}:{client_ip}"
        # INCR-затем-EXPIRE имеет микроокно гонки (упади процесс между ними —
        # ключ останется без TTL). Для MVP осознанно принято; Lua-скрипт — YAGNI.
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_sec)
        if count > limit:
            ttl = await redis.ttl(key)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many requests",
                headers={"Retry-After": str(max(ttl, 1))},
            )

    return dependency
