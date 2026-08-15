import pytest
import redis.exceptions
from httpx import ASGITransport, AsyncClient

from app.core.redis import get_redis
from app.services.cache import invalidate_catalog


class BrokenRedis:
    """Redis-клиент, который всегда падает — эмулирует недоступный Redis."""

    async def get(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("redis is down")

    async def set(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("redis is down")

    async def incr(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("redis is down")

    async def ttl(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("redis is down")

    async def expire(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("redis is down")

    def scan_iter(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("redis is down")

    async def delete(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("redis is down")


@pytest.fixture
def broken_redis():
    return BrokenRedis()


@pytest.fixture
async def broken_client(app, broken_redis):
    async def _get_redis():
        yield broken_redis

    app.dependency_overrides[get_redis] = _get_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_products_list_survives_broken_redis(broken_client, sample_data):
    r = await broken_client.get("/products")
    assert r.status_code == 200
    assert r.json()


async def test_product_detail_survives_broken_redis(broken_client, sample_data):
    r = await broken_client.get("/products/tank-pack-3d")
    assert r.status_code == 200


async def test_login_survives_broken_redis(broken_client):
    r = await broken_client.post(
        "/auth/login", json={"email": "ghost@b.c", "password": "wrong-pass"}
    )
    assert r.status_code == 401


async def test_invalidate_catalog_returns_zero_on_broken_redis(broken_redis):
    assert await invalidate_catalog(broken_redis) == 0
