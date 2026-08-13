import json

CATALOG_TTL = 300  # 5 минут по спеке §6


async def get_or_set(redis, key: str, ttl: int, loader):
    cached = await redis.get(key)
    if cached is not None:
        return json.loads(cached)
    value = await loader()
    await redis.set(key, json.dumps(value), ex=ttl)
    return value


async def invalidate_catalog(redis) -> int:
    keys = [k async for k in redis.scan_iter("cache:products:*")]
    if keys:
        await redis.delete(*keys)
    return len(keys)
