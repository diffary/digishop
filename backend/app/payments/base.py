from dataclasses import dataclass
from typing import Protocol


@dataclass
class CheckoutSession:
    session_id: str
    url: str


class PaymentProvider(Protocol):
    name: str

    async def create_checkout(
        self, *, order_id: int, amount_total: int, description: str
    ) -> CheckoutSession: ...

    def verify_webhook(self, payload: bytes, signature: str) -> dict: ...
