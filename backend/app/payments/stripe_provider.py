import asyncio
import time

import stripe

from app.core.config import get_settings
from app.payments.base import CheckoutSession, PaymentProvider


class StripeProvider:
    name = "stripe"

    async def create_checkout(
        self, *, order_id: int, amount_total: int, description: str
    ) -> CheckoutSession:
        settings = get_settings()
        stripe.api_key = settings.stripe_secret_key
        # stripe SDK синхронный — уводим в поток, чтобы не блокировать event loop
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": amount_total,  # центы, как везде в проекте
                        "product_data": {"name": description},
                    },
                    "quantity": 1,
                }
            ],
            metadata={"order_id": str(order_id)},
            success_url=f"{settings.frontend_url}/order/success?order_id={order_id}",
            cancel_url=f"{settings.frontend_url}/order/cancel",
            # сессия Stripe живёт ровно столько же, сколько наш pending-заказ —
            # иначе можно оплатить уже проваленный заказ
            expires_at=int(time.time()) + 3600,
        )
        return CheckoutSession(session_id=session.id, url=session.url)

    def verify_webhook(self, payload: bytes, signature: str) -> dict:
        settings = get_settings()
        # stripe.SignatureVerificationError пробрасывается наверх (роут ответит 400);
        # модуля stripe.error больше нет (удалён в SDK v8)
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
        # event.to_dict_recursive() отсутствует в stripe 15.x Event; to_dict() уже
        # рекурсивно разворачивает вложенные StripeObject в обычные dict/list
        return event.to_dict()


def get_payment_provider() -> PaymentProvider:
    return StripeProvider()
