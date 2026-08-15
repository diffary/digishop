from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import SessionDep
from app.payments.base import PaymentProvider
from app.payments.stripe_provider import get_payment_provider
from app.services.payments_flow import apply_payment
from app.tasks.delivery import deliver_order

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

ProviderDep = Annotated[PaymentProvider, Depends(get_payment_provider)]


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    session: SessionDep,
    provider: ProviderDep,
) -> dict:
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing stripe-signature header")

    payload = await request.body()
    try:
        event = provider.verify_webhook(payload, signature)
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid signature") from exc

    if event.get("type") != "checkout.session.completed":
        return {"status": "ok"}

    session_id = event["data"]["object"]["id"]
    order = await apply_payment(session, session_id)
    if order is not None:
        # тяжёлая работа в Celery, Stripe ждёт ответ секунды
        deliver_order.delay(order.id)

    return {"status": "ok"}
