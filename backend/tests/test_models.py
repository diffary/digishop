from sqlalchemy.ext.asyncio import create_async_engine

from app.core.db import Base
from app.models import Category, DownloadLink, Notification, Order, OrderItem, Product, User


async def test_all_tables_create():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    names = set(Base.metadata.tables)
    assert names == {
        "users", "categories", "products",
        "orders", "order_items", "download_links", "notifications",
    }
    await engine.dispose()
    assert User.__tablename__ == "users"
    assert Category.__tablename__ == "categories"
    assert Product.__tablename__ == "products"
    assert Order.__tablename__ == "orders"
    assert OrderItem.__tablename__ == "order_items"
    assert DownloadLink.__tablename__ == "download_links"
    assert Notification.__tablename__ == "notifications"
