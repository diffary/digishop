import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderStatus

logger = logging.getLogger(__name__)


async def apply_payment(session: AsyncSession, payment_session_id: str) -> Order | None:
    """Идемпотентный переход заказа pending→paid по платёжной сессии.

    Контракт (его же проверяют тесты tests/test_webhook.py):
    1. Найти Order по payment_session_id. Не нашёл — warning в лог, вернуть None.
    2. Статус НЕ pending — info в лог (повторный вебхук), вернуть None. Это идемпотентность.
    3. Иначе: перевести в paid, закоммитить, вернуть Order.

    Подсказки: select(Order).where(...), у результата есть .scalar_one_or_none();
    статусы сравнивать с OrderStatus.pending / присваивать OrderStatus.paid;
    logger.warning / logger.info уже импортированы.
    """
    result = await session.execute(
        select(Order).where(Order.payment_session_id == payment_session_id)
    )
    order = result.scalar_one_or_none()

    if order is None:
        logger.warning("Order with payment_session_id %s not found", payment_session_id)
        return None

    if order.status != OrderStatus.pending:
        logger.info("Order %s is not pending (current status: %s).", order.id, order.status)
        return None

    order.status = OrderStatus.paid
    order.paid_at = datetime.now(UTC)
    await session.commit()
    return order
