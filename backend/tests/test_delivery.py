from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import DownloadLink, Notification, Order, OrderItem, OrderStatus, User
from app.services.delivery import deliver
from app.tasks.delivery import deliver_order


async def _make_order(db_session, sample_data, status: OrderStatus) -> int:
    user = User(email="buyer@test.dev", password_hash="hash")
    db_session.add(user)
    await db_session.flush()

    order = Order(user_id=user.id, status=status, total=2998, provider="stripe")
    db_session.add(order)
    await db_session.flush()

    items = [
        OrderItem(order_id=order.id, product_id=1, price_at_purchase=1999),
        OrderItem(order_id=order.id, product_id=2, price_at_purchase=999),
    ]
    db_session.add_all(items)
    await db_session.commit()
    return order.id


async def test_deliver_creates_links_and_notification(db_session, sample_data):
    order_id = await _make_order(db_session, sample_data, OrderStatus.paid)

    await deliver(db_session, order_id)

    links = (await db_session.execute(select(DownloadLink))).scalars().all()
    assert len(links) == 2
    now = datetime.now(UTC)
    for link in links:
        assert link.download_count == 0
        expires_at = link.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        delta = expires_at - now
        assert timedelta(days=6) < delta < timedelta(days=8)

    notifications = (await db_session.execute(select(Notification))).scalars().all()
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.order_id == order_id
    assert notification.type == "order_delivered"
    tokens = notification.payload["tokens"]
    assert set(tokens) == {link.token for link in links}

    order = await db_session.get(Order, order_id)
    assert order.status == OrderStatus.delivered


async def test_deliver_idempotent_on_delivered(db_session, sample_data):
    order_id = await _make_order(db_session, sample_data, OrderStatus.paid)

    await deliver(db_session, order_id)
    await deliver(db_session, order_id)

    links = (await db_session.execute(select(DownloadLink))).scalars().all()
    notifications = (await db_session.execute(select(Notification))).scalars().all()
    assert len(links) == 2
    assert len(notifications) == 1

    order = await db_session.get(Order, order_id)
    assert order.status == OrderStatus.delivered


async def test_deliver_noop_on_pending(db_session, sample_data):
    order_id = await _make_order(db_session, sample_data, OrderStatus.pending)

    await deliver(db_session, order_id)

    links = (await db_session.execute(select(DownloadLink))).scalars().all()
    notifications = (await db_session.execute(select(Notification))).scalars().all()
    assert links == []
    assert notifications == []

    order = await db_session.get(Order, order_id)
    assert order.status == OrderStatus.pending


async def test_deliver_unknown_order(db_session, sample_data):
    await deliver(db_session, 999999)

    links = (await db_session.execute(select(DownloadLink))).scalars().all()
    notifications = (await db_session.execute(select(Notification))).scalars().all()
    assert links == []
    assert notifications == []


def test_deliver_order_task_runs_service(monkeypatch):
    recorded: list[int] = []

    async def fake_deliver(session, order_id):
        recorded.append(order_id)

    monkeypatch.setattr("app.services.delivery.deliver", fake_deliver)

    deliver_order.run(42)

    assert recorded == [42]
