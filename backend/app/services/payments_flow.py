import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus

logger = logging.getLogger(__name__)


async def apply_payment(session: AsyncSession, payment_session_id: str) -> Order | None:
    """Идемпотентный переход заказа pending→paid по платёжной сессии.

    Возвращает Order, если переход произошёл, иначе None (заказ не найден
    или уже обработан — повторный вебхук).
    """
    result = await session.execute(
        select(Order).where(Order.payment_session_id == payment_session_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        logger.warning("webhook: unknown payment_session_id %s", payment_session_id)
        return None
    if order.status != OrderStatus.pending:
        logger.info("webhook replay for order %s (status=%s) — no-op", order.id, order.status)
        return None
    order.status = OrderStatus.paid
    await session.commit()
    return order
