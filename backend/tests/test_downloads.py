from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import Category, DownloadLink, Order, OrderItem, OrderStatus, Product, User
from app.services.delivery import deliver


async def _delivered_link(db_session, file_key: str = "files/demo.zip") -> str:
    category = Category(name="Demo", slug="demo-cat")
    db_session.add(category)
    await db_session.flush()

    product = Product(
        category_id=category.id,
        name="Demo Product",
        slug="demo-product",
        description="demo",
        price=999,
        image_url=None,
        file_key=file_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()

    user = User(email="buyer@test.dev", password_hash="hash")
    db_session.add(user)
    await db_session.flush()

    order = Order(user_id=user.id, status=OrderStatus.paid, total=999, provider="stripe")
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(order_id=order.id, product_id=product.id, price_at_purchase=999)
    db_session.add(item)
    await db_session.commit()

    await deliver(db_session, order.id)

    link = (await db_session.execute(select(DownloadLink))).scalars().one()
    return link.token


@pytest.fixture
async def delivered_order(db_session):
    return await _delivered_link(db_session)


async def test_download_with_valid_token(client, delivered_order, db_session):
    token = delivered_order
    r = await client.get(f"/downloads/{token}")
    assert r.status_code == 200
    assert r.headers["content-type"] in ("application/zip", "application/octet-stream")
    assert len(r.content) > 0

    link = (
        await db_session.execute(select(DownloadLink).where(DownloadLink.token == token))
    ).scalar_one()
    assert link.download_count == 1


async def test_download_twice_allowed(client, delivered_order, db_session):
    token = delivered_order
    r1 = await client.get(f"/downloads/{token}")
    assert r1.status_code == 200
    r2 = await client.get(f"/downloads/{token}")
    assert r2.status_code == 200

    link = (
        await db_session.execute(select(DownloadLink).where(DownloadLink.token == token))
    ).scalar_one()
    assert link.download_count == 2


async def test_download_expired_token_410(client, delivered_order, db_session):
    token = delivered_order
    link = (
        await db_session.execute(select(DownloadLink).where(DownloadLink.token == token))
    ).scalar_one()
    link.expires_at = datetime.now(UTC) - timedelta(days=1)
    await db_session.commit()

    r = await client.get(f"/downloads/{token}")
    assert r.status_code == 410


async def test_download_unknown_token_404(client):
    r = await client.get("/downloads/deadbeef")
    assert r.status_code == 404


async def test_download_missing_file_404(client, db_session):
    token = await _delivered_link(db_session, file_key="files/no-such.zip")
    r = await client.get(f"/downloads/{token}")
    assert r.status_code == 404
