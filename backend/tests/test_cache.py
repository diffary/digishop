async def test_products_response_is_cached(client, sample_data, fake_redis):
    await client.get("/products")
    keys = await fake_redis.keys("cache:products:*")
    assert keys


async def test_cache_key_varies_by_query(client, sample_data, fake_redis):
    await client.get("/products")
    await client.get("/products", params={"category": "game-assets"})
    keys = await fake_redis.keys("cache:products:list:*")
    assert len(keys) == 2


async def test_cache_hit_skips_db(client, sample_data, fake_redis, monkeypatch):
    r1 = await client.get("/products")
    assert r1.status_code == 200

    import app.api.products as products_api

    async def boom(*a, **kw):
        raise AssertionError("DB was hit on cache hit")

    monkeypatch.setattr(products_api, "list_products", boom)
    r2 = await client.get("/products")
    assert r2.status_code == 200
    assert r2.json() == r1.json()


async def test_detail_cached(client, sample_data, fake_redis):
    await client.get("/products/tank-pack-3d")
    keys = await fake_redis.keys("cache:products:detail:tank-pack-3d")
    assert keys


async def test_cache_respects_ttl_setting(client, sample_data, fake_redis):
    await client.get("/products")
    keys = await fake_redis.keys("cache:products:list:*")
    ttl = await fake_redis.ttl(keys[0])
    assert 0 < ttl <= 300


async def test_invalidate_catalog(client, sample_data, fake_redis):
    await client.get("/products")
    from app.services.cache import invalidate_catalog

    await invalidate_catalog(fake_redis)
    assert not await fake_redis.keys("cache:products:*")
