import json

CATALOG_TTL = 300  # 5 минут по спеке §6


async def get_or_set(redis, key: str, ttl: int, loader):
    """Cache-aside: верни из кэша по key, а на промахе — сходи в loader,
    положи результат в кэш с ttl и верни его.

    redis — асинхронный клиент (get/set), в кэше лежат СТРОКИ.
    loader — async-функция без аргументов, возвращает JSON-сериализуемое.
    """
    value = await redis.get(key)
    if value is not None:
        return json.loads(value)  # ТВОЁ УПРАЖНЕНИЕ №1
    else:
        value = await loader()
        await redis.set(key, json.dumps(value), ex=ttl)
        return value  # ТВОЁ УПРАЖНЕНИЕ №2


async def invalidate_catalog(redis) -> int:
    """Удали все ключи cache:products:* и верни, сколько удалил.

    Подсказка: redis.scan_iter(pattern) — АСИНХРОННЫЙ генератор.
    """
    keys_to_delete = []
    async for key in redis.scan_iter(match="cache:products:*"):
        keys_to_delete.append(key)

    if keys_to_delete:
        await redis.delete(*keys_to_delete)
    return len(keys_to_delete)  # ТВОЁ УПРАЖНЕНИЕ №2

