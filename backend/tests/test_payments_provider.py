import stripe

from app.core.config import get_settings
from app.payments.base import CheckoutSession
from app.payments.stripe_provider import StripeProvider, get_payment_provider


class FakeSession:
    id = "cs_test_123"
    url = "https://checkout.stripe.test/cs_test_123"


async def test_create_checkout_builds_session(monkeypatch):
    recorded = {}

    def fake_create(**kwargs):
        recorded.update(kwargs)
        return FakeSession()

    monkeypatch.setattr(stripe.checkout.Session, "create", staticmethod(fake_create))

    provider = StripeProvider()
    result = await provider.create_checkout(
        order_id=7, amount_total=2998, description="DigiShop order #7"
    )

    assert result == CheckoutSession(session_id="cs_test_123", url=FakeSession.url)

    assert recorded["mode"] == "payment"
    assert len(recorded["line_items"]) == 1
    line_item = recorded["line_items"][0]
    assert line_item["quantity"] == 1
    assert line_item["price_data"]["unit_amount"] == 2998
    assert line_item["price_data"]["currency"] == "usd"
    assert recorded["metadata"] == {"order_id": "7"}

    settings = get_settings()
    assert recorded["success_url"].startswith(settings.frontend_url)
    assert "/order/success?order_id=7" in recorded["success_url"]
    assert "/order/cancel" in recorded["cancel_url"]


def test_verify_webhook_returns_dict(monkeypatch):
    fake_event = stripe.Event.construct_from(
        {
            "id": "evt_1",
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_123"}},
        },
        "sk_test",
    )

    def fake_construct_event(payload, signature, secret):
        return fake_event

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    provider = StripeProvider()
    result = provider.verify_webhook(b"{}", "sig")

    assert isinstance(result, dict)
    assert result["type"] == "checkout.session.completed"
    assert result["data"]["object"]["id"] == "cs_test_123"


def test_verify_webhook_raises_on_bad_signature(monkeypatch):
    def fake_construct_event(payload, signature, secret):
        raise stripe.SignatureVerificationError("bad", "sig")

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct_event)

    provider = StripeProvider()
    try:
        provider.verify_webhook(b"{}", "sig")
    except stripe.SignatureVerificationError:
        pass
    else:
        raise AssertionError("expected SignatureVerificationError to propagate")


def test_get_payment_provider_returns_stripe():
    assert get_payment_provider().name == "stripe"
