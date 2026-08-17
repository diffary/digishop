from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import DownloadLink, Order, OrderItem, OrderStatus, User
from app.services.maintenance import (
    cleanup_expired_links,
    expire_stale_pending,
    find_undelivered_paid,
)
from app.tasks.maintenance import (
    check_undelivered_paid,
    cleanup_expired_links_task,
    expire_pending_orders,
)


async def _make_user(db_session) -> int:
    user = User(email="buyer@test.dev", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    return user.id


async def _make_order(db_session, user_id, status, created_at, paid_at=None) -> Order:
    order = Order(user_id=user_id, status=status, total=1999, provider="stripe")
    db_session.add(order)
    await db_session.flush()
    order.created_at = created_at
    order.paid_at = paid_at
    return order


async def test_expire_pending_orders(db_session, sample_data):
    user_id = await _make_user(db_session)
    now = datetime.now(UTC)

    old_pending = await _make_order(
        db_session, user_id, OrderStatus.pending, now - timedelta(hours=2)
    )
    fresh_pending = await _make_order(
        db_session, user_id, OrderStatus.pending, now - timedelta(minutes=10)
    )
    old_paid = await _make_order(db_session, user_id, OrderStatus.paid, now - timedelta(hours=2))
    await db_session.commit()

    count = await expire_stale_pending(db_session)
    assert count == 1

    await db_session.refresh(old_pending)
    await db_session.refresh(fresh_pending)
    await db_session.refresh(old_paid)

    assert old_pending.status == OrderStatus.failed
    assert fresh_pending.status == OrderStatus.pending
    assert old_paid.status == OrderStatus.paid


async def test_expire_pending_orders_inside_grace_not_failed(db_session, sample_data):
    user_id = await _make_user(db_session)
    now = datetime.now(UTC)

    within_grace = await _make_order(
        db_session, user_id, OrderStatus.pending, now - timedelta(minutes=65)
    )
    await db_session.commit()

    count = await expire_stale_pending(db_session)
    assert count == 0

    await db_session.refresh(within_grace)
    assert within_grace.status == OrderStatus.pending


async def test_expire_pending_orders_none_stale(db_session, sample_data):
    user_id = await _make_user(db_session)
    now = datetime.now(UTC)
    fresh_pending = await _make_order(
        db_session, user_id, OrderStatus.pending, now - timedelta(minutes=5)
    )
    await db_session.commit()

    count = await expire_stale_pending(db_session)
    assert count == 0

    await db_session.refresh(fresh_pending)
    assert fresh_pending.status == OrderStatus.pending


async def test_cleanup_expired_links(db_session, sample_data):
    user_id = await _make_user(db_session)
    now = datetime.now(UTC)
    order = await _make_order(db_session, user_id, OrderStatus.delivered, now)
    item = OrderItem(order_id=order.id, product_id=1, price_at_purchase=1999)
    db_session.add(item)
    await db_session.flush()

    expired_link = DownloadLink(order_item_id=item.id, expires_at=now - timedelta(days=1))
    alive_link = DownloadLink(order_item_id=item.id, expires_at=now + timedelta(days=6))
    db_session.add_all([expired_link, alive_link])
    await db_session.commit()

    count = await cleanup_expired_links(db_session)
    assert count == 1

    remaining = (await db_session.execute(select(DownloadLink))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].id == alive_link.id


async def test_find_undelivered_paid(db_session, sample_data):
    user_id = await _make_user(db_session)
    now = datetime.now(UTC)

    undelivered = await _make_order(
        db_session,
        user_id,
        OrderStatus.paid,
        now - timedelta(minutes=30),
        paid_at=now - timedelta(minutes=30),
    )

    delivered = await _make_order(
        db_session,
        user_id,
        OrderStatus.delivered,
        now - timedelta(minutes=30),
        paid_at=now - timedelta(minutes=30),
    )
    delivered_item = OrderItem(order_id=delivered.id, product_id=1, price_at_purchase=1999)
    db_session.add(delivered_item)
    await db_session.flush()
    db_session.add(
        DownloadLink(order_item_id=delivered_item.id, expires_at=now + timedelta(days=6))
    )

    fresh_paid = await _make_order(
        db_session,
        user_id,
        OrderStatus.paid,
        now - timedelta(minutes=5),
        paid_at=now - timedelta(minutes=5),
    )
    await db_session.commit()

    ids = await find_undelivered_paid(db_session, older_than_minutes=15)

    assert undelivered.id in ids
    assert delivered.id not in ids
    assert fresh_paid.id not in ids


async def test_find_undelivered_paid_no_false_positive_from_created_at(db_session, sample_data):
    """created_at=12:00, paid_at=12:50, checked=12:55 (older_than=15 -> cutoff 12:40):
    заказ оплачен недавно (5 минут назад), несмотря на то, что создан был >15 минут назад —
    не должен попадать в мониторинг."""
    user_id = await _make_user(db_session)
    checked_at = datetime(2026, 1, 1, 12, 55, tzinfo=UTC)
    created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    paid_at = datetime(2026, 1, 1, 12, 50, tzinfo=UTC)

    order = await _make_order(db_session, user_id, OrderStatus.paid, created_at, paid_at=paid_at)
    await db_session.commit()

    ids = await find_undelivered_paid(db_session, older_than_minutes=15, now=checked_at)

    assert order.id not in ids


async def test_find_undelivered_paid_legacy_row_without_paid_at_uses_created_at(
    db_session, sample_data
):
    """У старых заказов (до миграции) paid_at может быть NULL — тогда используем
    created_at как фолбэк, чтобы не потерять мониторинг."""
    user_id = await _make_user(db_session)
    now = datetime.now(UTC)

    legacy_undelivered = await _make_order(
        db_session, user_id, OrderStatus.paid, now - timedelta(minutes=30), paid_at=None
    )
    await db_session.commit()

    ids = await find_undelivered_paid(db_session, older_than_minutes=15)

    assert legacy_undelivered.id in ids


def test_expire_pending_orders_task_runs_service(monkeypatch):
    recorded: list[str] = []

    async def fake_expire_stale_pending(session):
        recorded.append("called")
        return 1

    monkeypatch.setattr("app.services.maintenance.expire_stale_pending", fake_expire_stale_pending)

    expire_pending_orders.run()

    assert recorded == ["called"]


def test_cleanup_expired_links_task_runs_service(monkeypatch):
    recorded: list[str] = []

    async def fake_cleanup_expired_links(session):
        recorded.append("called")
        return 1

    monkeypatch.setattr(
        "app.services.maintenance.cleanup_expired_links", fake_cleanup_expired_links
    )

    cleanup_expired_links_task.run()

    assert recorded == ["called"]


def test_check_undelivered_paid_task_runs_service(monkeypatch):
    recorded: list[str] = []

    async def fake_find_undelivered_paid(session, older_than_minutes=15):
        recorded.append("called")
        return []

    monkeypatch.setattr(
        "app.services.maintenance.find_undelivered_paid", fake_find_undelivered_paid
    )

    check_undelivered_paid.run()

    assert recorded == ["called"]
