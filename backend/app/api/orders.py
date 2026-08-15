from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.payments.base import PaymentProvider
from app.payments.stripe_provider import get_payment_provider
from app.schemas.orders import OrderCreateIn, OrderCreateOut, OrderItemOut, OrderOut
from app.services.orders import InvalidProductsError, create_order, get_order, list_orders

router = APIRouter(prefix="/orders", tags=["orders"])

ProviderDep = Annotated[PaymentProvider, Depends(get_payment_provider)]


@router.post("", response_model=OrderCreateOut, status_code=status.HTTP_201_CREATED)
async def create_order_endpoint(
    data: OrderCreateIn,
    user: CurrentUser,
    session: SessionDep,
    provider: ProviderDep,
) -> OrderCreateOut:
    try:
        order, checkout_url = await create_order(session, user.id, data.product_ids, provider)
    except InvalidProductsError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid or inactive product ids: {exc.missing_ids}",
        ) from exc
    return OrderCreateOut(order_id=order.id, checkout_url=checkout_url)


@router.get("", response_model=list[OrderOut])
async def list_orders_endpoint(user: CurrentUser, session: SessionDep) -> list[OrderOut]:
    orders = await list_orders(session, user.id)
    return [
        OrderOut(
            id=order.id,
            status=order.status,
            total=order.total,
            created_at=order.created_at,
            items=[
                OrderItemOut(product_id=i.product_id, price_at_purchase=i.price_at_purchase)
                for i in items
            ],
        )
        for order, items in orders
    ]


@router.get("/{order_id}", response_model=OrderOut)
async def get_order_endpoint(order_id: int, user: CurrentUser, session: SessionDep) -> OrderOut:
    result = await get_order(session, user.id, order_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    order, items = result
    return OrderOut(
        id=order.id,
        status=order.status,
        total=order.total,
        created_at=order.created_at,
        items=[
            OrderItemOut(product_id=i.product_id, price_at_purchase=i.price_at_purchase)
            for i in items
        ],
    )
