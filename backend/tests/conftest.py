import os

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-bytes-long")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import fakeredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_session
from app.core.redis import get_redis
from app.main import create_app
from app.models import Category, Product


@pytest.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def fake_redis():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


@pytest.fixture
async def client(session_factory, fake_redis):
    async def _get_session():
        async with session_factory() as session:
            yield session

    async def _get_redis():
        yield fake_redis

    app = create_app()
    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_redis] = _get_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture
async def sample_data(db_session):
    game_assets = Category(name="Игровые ассеты", slug="game-assets")
    templates = Category(name="Шаблоны", slug="templates")
    db_session.add_all([game_assets, templates])
    await db_session.flush()

    products = [
        Product(
            category_id=game_assets.id,
            name="Tank Pack 3D",
            slug="tank-pack-3d",
            description="3D tank models",
            price=1999,
            image_url=None,
            file_key="files/tank-pack-3d.zip",
            is_active=True,
        ),
        Product(
            category_id=game_assets.id,
            name="Pixel UI Kit",
            slug="pixel-ui-kit",
            description="Pixel art UI kit",
            price=999,
            image_url=None,
            file_key="files/pixel-ui-kit.zip",
            is_active=True,
        ),
        Product(
            category_id=templates.id,
            name="Old Bundle",
            slug="old-bundle",
            description="Deprecated bundle",
            price=499,
            image_url=None,
            file_key="files/old-bundle.zip",
            is_active=False,
        ),
    ]
    db_session.add_all(products)
    await db_session.commit()
