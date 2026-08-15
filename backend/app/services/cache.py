import json
import logging

from redis import exceptions as redis_exceptions

CATALOG_TTL = 300  # 5 минут по спеке §6

logger = logging.getLogger(__name__)


async def get_or_set(redis, key: str, ttl: int, loader):
    """Cache-aside: верни из кэша по key, а на промахе — сходи в loader,
    положи результат в кэш с ttl и верни его.

    redis — асинхронный клиент (get/set), в кэше лежат СТРОКИ.
    loader — async-функция без аргументов, возвращает JSON-сериализуемое.

    Кэш не должен класть сайт — fail-open по решению ревью: если Redis
    недоступен, идём мимо кэша прямо в loader.
    """
    value = None
    try:
        value = await redis.get(key)
    except redis_exceptions.RedisError:
        logger.warning("redis get failed for key=%s, falling back to loader", key)

    if value is not None:
        return json.loads(value)

    value = await loader()
    try:
        await redis.set(key, json.dumps(value), ex=ttl)
    except redis_exceptions.RedisError:
        logger.warning("redis set failed for key=%s, serving uncached value", key)
    return value


async def invalidate_catalog(redis) -> int:
    """Удали все ключи cache:products:* и верни, сколько удалил.

    Подсказка: redis.scan_iter(pattern) — АСИНХРОННЫЙ генератор.
    """
    keys_to_delete = []
    try:
        async for key in redis.scan_iter(match="cache:products:*"):
            keys_to_delete.append(key)

        if keys_to_delete:
            await redis.delete(*keys_to_delete)
    except redis_exceptions.RedisError:
        logger.warning("redis unavailable, could not invalidate catalog cache")
        return 0
    return len(keys_to_delete)
