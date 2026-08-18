from sqlalchemy import select

from app.models import DownloadLink, Order, OrderItem, OrderStatus, Product, User
from app.services.delivery import deliver


async def _product_ids(db_session, slugs):
    result = await db_session.execute(select(Product).where(Product.slug.in_(slugs)))
    products = {p.slug: p for p in result.scalars().all()}
    return products


async def test_create_order_happy_path(auth_client, sample_data, fake_provider, db_session):
    products = await _product_ids(db_session, ["tank-pack-3d", "pixel-ui-kit"])
    tank_id = products["tank-pack-3d"].id
    pixel_id = products["pixel-ui-kit"].id

    r = await auth_client.post("/orders", json={"product_ids": [tank_id, pixel_id]})

    assert r.status_code == 201
    body = r.json()
    assert isinstance(body["order_id"], int)
    assert body["checkout_url"] == "https://pay.fake/cs_fake_1"

    assert len(fake_provider.calls) == 1
    call = fake_provider.calls[0]
    assert call["amount_total"] == 2998
    assert call["order_id"] == body["order_id"]

    order = await db_session.get(Order, body["order_id"])
    assert order.status == OrderStatus.pending
    assert order.total == 2998
    assert order.payment_session_id == "cs_fake_1"
    assert order.provider == "fake"

    items = (
        (await db_session.execute(select(OrderItem).where(OrderItem.order_id == order.id)))
        .scalars()
        .all()
    )
    assert len(items) == 2
    prices = sorted(i.price_at_purchase for i in items)
    assert prices == [999, 1999]


async def test_create_order_ignores_client_prices(
    auth_client, sample_data, fake_provider, db_session
):
    products = await _product_ids(db_session, ["tank-pack-3d"])
    tank = products["tank-pack-3d"]
    tank.price = 12345
    await db_session.commit()

    r = await auth_client.post("/orders", json={"product_ids": [tank.id]})

    assert r.status_code == 201
    order = await db_session.get(Order, r.json()["order_id"])
    assert order.total == 12345


async def test_create_order_rejects_inactive(auth_client, sample_data, fake_provider, db_session):
    products = await _product_ids(db_session, ["old-bundle"])
    r = await auth_client.post("/orders", json={"product_ids": [products["old-bundle"].id]})
    assert r.status_code == 422

    count = (await db_session.execute(select(Order))).scalars().all()
    assert count == []


async def test_create_order_rejects_unknown(auth_client, sample_data, fake_provider):
    r = await auth_client.post("/orders", json={"product_ids": [999999]})
    assert r.status_code == 422


async def test_create_order_empty_list(auth_client, sample_data, fake_provider):
    r = await auth_client.post("/orders", json={"product_ids": []})
    assert r.status_code == 422


async def test_create_order_dedupes(auth_client, sample_data, fake_provider, db_session):
    products = await _product_ids(db_session, ["tank-pack-3d"])
    tank_id = products["tank-pack-3d"].id

    r = await auth_client.post("/orders", json={"product_ids": [tank_id, tank_id]})

    assert r.status_code == 201
    order = await db_session.get(Order, r.json()["order_id"])
    assert order.total == 1999

    items = (
        (await db_session.execute(select(OrderItem).where(OrderItem.order_id == order.id)))
        .scalars()
        .all()
    )
    assert len(items) == 1


async def test_create_order_requires_auth(client, sample_data, fake_provider, db_session):
    products = await _product_ids(db_session, ["tank-pack-3d"])
    r = await client.post("/orders", json={"product_ids": [products["tank-pack-3d"].id]})
    assert r.status_code == 401


async def test_list_orders_own_only(auth_client, sample_data, fake_provider, db_session, client):
    products = await _product_ids(db_session, ["tank-pack-3d"])
    tank_id = products["tank-pack-3d"].id
    await auth_client.post("/orders", json={"product_ids": [tank_id]})

    r = await client.post(
        "/auth/register", json={"email": "other@test.dev", "password": "pass12345"}
    )
    assert r.status_code == 201
    r = await client.post("/auth/login", json={"email": "other@test.dev", "password": "pass12345"})
    other_token = r.json()["access_token"]

    r = await client.get("/orders", headers={"Authorization": f"Bearer {other_token}"})
    assert r.status_code == 200
    assert r.json() == []

    r = await auth_client.get("/orders")
    assert r.status_code == 200
    orders = r.json()
    assert len(orders) == 1
    assert orders[0]["status"] == "pending"
    assert orders[0]["items"][0]["product_id"] == tank_id
    assert orders[0]["items"][0]["price_at_purchase"] == 1999


async def test_get_order_by_id(auth_client, sample_data, fake_provider, db_session, client):
    products = await _product_ids(db_session, ["tank-pack-3d"])
    tank_id = products["tank-pack-3d"].id
    r = await auth_client.post("/orders", json={"product_ids": [tank_id]})
    order_id = r.json()["order_id"]

    r = await auth_client.get(f"/orders/{order_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == order_id
    assert body["items"][0]["product_id"] == tank_id

    r = await client.post(
        "/auth/register", json={"email": "other2@test.dev", "password": "pass12345"}
    )
    assert r.status_code == 201
    r = await client.post("/auth/login", json={"email": "other2@test.dev", "password": "pass12345"})
    other_token = r.json()["access_token"]

    r = await client.get(f"/orders/{order_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert r.status_code == 404

    r = await auth_client.get("/orders/999999")
    assert r.status_code == 404


async def test_cors_header_for_frontend_origin(client, sample_data):
    r = await client.get("/products", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_order_detail_includes_download_tokens_when_delivered(
    auth_client, sample_data, db_session
):
    products = await _product_ids(db_session, ["tank-pack-3d"])
    tank = products["tank-pack-3d"]

    user = (
        (await db_session.execute(select(User).where(User.email == "buyer@test.dev")))
        .scalars()
        .one()
    )

    order = Order(user_id=user.id, status=OrderStatus.paid, total=tank.price, provider="stripe")
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(order_id=order.id, product_id=tank.id, price_at_purchase=tank.price)
    db_session.add(item)
    await db_session.commit()

    await deliver(db_session, order.id)

    r = await auth_client.get(f"/orders/{order.id}")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    item_out = body["items"][0]
    assert item_out["product_name"] == "Tank Pack 3D"
    # токен обязан совпадать с реальным DownloadLink в БД, а не быть просто строкой
    db_link = (
        (
            await db_session.execute(
                select(DownloadLink).where(DownloadLink.order_item_id == item.id)
            )
        )
        .scalars()
        .one()
    )
    assert item_out["download_token"] == db_link.token


async def test_order_detail_download_token_null_when_pending(
    auth_client, sample_data, fake_provider, db_session
):
    products = await _product_ids(db_session, ["tank-pack-3d"])
    tank_id = products["tank-pack-3d"].id

    r = await auth_client.post("/orders", json={"product_ids": [tank_id]})
    assert r.status_code == 201
    order_id = r.json()["order_id"]

    r = await auth_client.get(f"/orders/{order_id}")
    assert r.status_code == 200
    body = r.json()
    item_out = body["items"][0]
    assert item_out["download_token"] is None
    assert item_out["product_name"] == "Tank Pack 3D"
