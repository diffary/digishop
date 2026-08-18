from datetime import datetime

from pydantic import BaseModel, Field

from app.models.order import OrderStatus


class OrderCreateIn(BaseModel):
    product_ids: list[int] = Field(min_length=1, max_length=50)


class OrderCreateOut(BaseModel):
    order_id: int
    checkout_url: str


class OrderItemOut(BaseModel):
    product_id: int
    price_at_purchase: int
    product_name: str
    download_token: str | None = None


class OrderOut(BaseModel):
    id: int
    status: OrderStatus
    total: int
    created_at: datetime
    items: list[OrderItemOut]
