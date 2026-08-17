import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DownloadLink, Order, OrderItem, OrderStatus

logger = logging.getLogger(__name__)

PENDING_TTL_HOURS = 1
UNDELIVERED_GRACE_MINUTES = 15
# Stripe Checkout Session живёт ровно PENDING_TTL_HOURS (см. stripe_provider.create_checkout,
# expires_at), но вебхук об оплате может прийти с задержкой — даём 15 минут запаса,
# чтобы не завалить заказ, который уже оплачен, но вебхук ещё не долетел.
PENDING_EXPIRY_GRACE_MINUTES = 15


async def expire_stale_pending(session: AsyncSession, now: datetime | None = None) -> int:
    """Помечает старые pending-заказы как failed.

    cutoff = 1ч (срок жизни Stripe-сессии) + 15 мин запаса на задержку вебхука.
    """
    cutoff = (now or datetime.now(UTC)) - timedelta(
        hours=PENDING_TTL_HOURS, minutes=PENDING_EXPIRY_GRACE_MINUTES
    )
    result = await session.execute(
        update(Order)
        .where(Order.status == OrderStatus.pending, Order.created_at < cutoff)
        .values(status=OrderStatus.failed)
    )
    await session.commit()
    count = result.rowcount or 0
    if count:
        logger.info("expire_stale_pending: %d orders expired", count)
    # Заказы, попавшие в failed здесь, больше не нужно отдельно мониторить на предмет
    # «оплачен после провала»: Stripe-сессия истекает через 1ч (см. stripe_provider),
    # а мы заваливаем pending только через 75 мин — оплатить уже проваленный заказ
    # невозможно by construction, значит find_undelivered_paid не должен знать про failed.
    return count


async def cleanup_expired_links(session: AsyncSession, now: datetime | None = None) -> int:
    """Удаляет просроченные DownloadLink (эндпоинт скачивания сам их не примет —
    задача лишь чистит мусор, см. spec §6)."""
    cutoff = now or datetime.now(UTC)
    result = await session.execute(delete(DownloadLink).where(DownloadLink.expires_at < cutoff))
    await session.commit()
    count = result.rowcount or 0
    if count:
        logger.info("cleanup_expired_links: %d links deleted", count)
    return count


async def find_undelivered_paid(
    session: AsyncSession,
    older_than_minutes: int = UNDELIVERED_GRACE_MINUTES,
    now: datetime | None = None,
) -> list[int]:
    """Ищет заказы status=paid старше N минут, у которых ни один OrderItem
    не имеет DownloadLink — «оплачен, но не доставлен» (мониторинг окна
    недоступности брокера). Пока просто логируем WARNING, позже — Sentry.

    Отсчитываем от paid_at (момента оплаты), а не created_at — иначе заказ,
    оплаченный за пару минут до проверки, но созданный давно, ложно попадал бы
    в список (см. тест test_find_undelivered_paid_no_false_positive_from_created_at).
    Для старых записей без paid_at (до этой миграции) фолбэк на created_at.
    """
    cutoff = (now or datetime.now(UTC)) - timedelta(minutes=older_than_minutes)

    delivered_order_ids = select(OrderItem.order_id).join(
        DownloadLink, DownloadLink.order_item_id == OrderItem.id
    )

    result = await session.execute(
        select(Order.id).where(
            Order.status == OrderStatus.paid,
            func.coalesce(Order.paid_at, Order.created_at) < cutoff,
            Order.id.not_in(delivered_order_ids),
        )
    )
    ids = [row[0] for row in result.all()]
    if ids:
        logger.warning("find_undelivered_paid: undelivered paid orders %s", ids)
    return ids
