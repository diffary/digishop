from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderItem, Product
from app.payments.base import PaymentProvider


class InvalidProductsError(Exception):
    def __init__(self, missing_ids: list[int]) -> None:
        self.missing_ids = missing_ids
        super().__init__(f"Invalid or inactive product ids: {missing_ids}")


async def create_order(
    session: AsyncSession,
    user_id: int,
    product_ids: list[int],
    provider: PaymentProvider,
) -> tuple[Order, str]:
    unique_ids = list(dict.fromkeys(product_ids))

    result = await session.execute(
        select(Product).where(Product.id.in_(unique_ids), Product.is_active.is_(True))
    )
    products = {p.id: p for p in result.scalars().all()}

    missing = [pid for pid in unique_ids if pid not in products]
    if missing:
        raise InvalidProductsError(missing)

    total = sum(products[pid].price for pid in unique_ids)

    order = Order(user_id=user_id, total=total, provider=provider.name)
    session.add(order)
    await session.flush()

    for pid in unique_ids:
        session.add(
            OrderItem(order_id=order.id, product_id=pid, price_at_purchase=products[pid].price)
        )

    checkout = await provider.create_checkout(
        order_id=order.id,
        amount_total=total,
        description=f"DigiShop order #{order.id}",
    )
    order.payment_session_id = checkout.session_id

    await session.commit()
    await session.refresh(order)

    return order, checkout.url


async def list_orders(session: AsyncSession, user_id: int) -> list[tuple[Order, list[OrderItem]]]:
    result = await session.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    orders = result.scalars().all()
    if not orders:
        return []

    order_ids = [o.id for o in orders]
    items_result = await session.execute(select(OrderItem).where(OrderItem.order_id.in_(order_ids)))
    items_by_order: dict[int, list[OrderItem]] = {oid: [] for oid in order_ids}
    for item in items_result.scalars().all():
        items_by_order[item.order_id].append(item)

    return [(order, items_by_order[order.id]) for order in orders]


async def get_order(
    session: AsyncSession, user_id: int, order_id: int
) -> tuple[Order, list[OrderItem]] | None:
    order = await session.get(Order, order_id)
    if order is None or order.user_id != user_id:
        return None

    items_result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    items = list(items_result.scalars().all())
    return order, items
