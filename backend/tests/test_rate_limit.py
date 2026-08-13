async def test_login_rate_limited(client):
    for _ in range(10):
        r = await client.post("/auth/login", json={"email": "x@y.z", "password": "wrong-pass"})
        assert r.status_code == 401
    r = await client.post("/auth/login", json={"email": "x@y.z", "password": "wrong-pass"})
    assert r.status_code == 429
    assert "Retry-After" in r.headers


async def test_register_rate_limited(client):
    for i in range(10):
        await client.post("/auth/register", json={"email": f"u{i}@y.z", "password": "pass1234"})
    r = await client.post("/auth/register", json={"email": "u10@y.z", "password": "pass1234"})
    assert r.status_code == 429


async def test_rate_limit_keys_use_own_prefix(client, fake_redis):
    await client.post("/auth/login", json={"email": "x@y.z", "password": "wrong-pass"})
    assert await fake_redis.keys("ratelimit:*")
    assert not await fake_redis.keys("cache:ratelimit*")


async def test_products_not_rate_limited(client, sample_data):
    for _ in range(15):
        r = await client.get("/products")
        assert r.status_code == 200
