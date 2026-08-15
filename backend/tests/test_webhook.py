import stripe
from httpx import AsyncClient
from sqlalchemy import select

from app.models import Order, OrderStatus


async def make_paid_ready_order(auth_client: AsyncClient) -> int:
    r = await auth_client.post("/orders", json={"product_ids": [1, 2]})
    assert r.status_code == 201
    return r.json()["order_id"]


async def test_webhook_marks_order_paid_and_enqueues_delivery(
    auth_client, sample_data, fake_provider, db_session, monkeypatch
):
    order_id = await make_paid_ready_order(auth_client)

    fake_provider.webhook_event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_fake_1"}},
    }

    calls: list[int] = []
    monkeypatch.setattr(
        "app.api.webhooks.deliver_order.delay", lambda order_id: calls.append(order_id)
    )

    r = await auth_client.post("/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})
    assert r.status_code == 200

    result = await db_session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one()
    assert order.status == OrderStatus.paid
    assert calls == [order_id]


async def test_webhook_idempotent_on_replay(
    auth_client, sample_data, fake_provider, db_session, monkeypatch
):
    order_id = await make_paid_ready_order(auth_client)

    fake_provider.webhook_event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_fake_1"}},
    }

    calls: list[int] = []
    monkeypatch.setattr(
        "app.api.webhooks.deliver_order.delay", lambda order_id: calls.append(order_id)
    )

    r1 = await auth_client.post(
        "/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"}
    )
    r2 = await auth_client.post(
        "/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"}
    )
    assert r1.status_code == 200
    assert r2.status_code == 200

    result = await db_session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one()
    assert order.status == OrderStatus.paid
    assert calls == [order_id]


async def test_webhook_bad_signature_400(auth_client, sample_data, fake_provider, monkeypatch):
    await make_paid_ready_order(auth_client)

    fake_provider.webhook_error = stripe.SignatureVerificationError("bad", "sig")

    calls: list[int] = []
    monkeypatch.setattr(
        "app.api.webhooks.deliver_order.delay", lambda order_id: calls.append(order_id)
    )

    r = await auth_client.post("/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})
    assert r.status_code == 400
    assert calls == []


async def test_webhook_unknown_session_200(
    auth_client, sample_data, fake_provider, db_session, monkeypatch
):
    order_id = await make_paid_ready_order(auth_client)

    fake_provider.webhook_event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_unknown"}},
    }

    calls: list[int] = []
    monkeypatch.setattr(
        "app.api.webhooks.deliver_order.delay", lambda order_id: calls.append(order_id)
    )

    r = await auth_client.post("/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})
    assert r.status_code == 200

    result = await db_session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one()
    assert order.status == OrderStatus.pending
    assert calls == []


async def test_webhook_other_event_type_200(
    auth_client, sample_data, fake_provider, db_session, monkeypatch
):
    order_id = await make_paid_ready_order(auth_client)

    fake_provider.webhook_event = {
        "type": "payment_intent.created",
        "data": {"object": {"id": "cs_fake_1"}},
    }

    calls: list[int] = []
    monkeypatch.setattr(
        "app.api.webhooks.deliver_order.delay", lambda order_id: calls.append(order_id)
    )

    r = await auth_client.post("/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})
    assert r.status_code == 200

    result = await db_session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one()
    assert order.status == OrderStatus.pending
    assert calls == []


async def test_webhook_missing_signature_header_400(
    auth_client, sample_data, fake_provider, monkeypatch
):
    calls: list[int] = []
    monkeypatch.setattr(
        "app.api.webhooks.deliver_order.delay", lambda order_id: calls.append(order_id)
    )

    r = await auth_client.post("/webhooks/stripe", content=b"{}")
    assert r.status_code == 400
    assert calls == []
