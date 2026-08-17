from datetime import UTC, datetime

from app.models import Order, OrderStatus, User
from app.services.payments_flow import apply_payment


async def test_apply_payment_sets_paid_at(db_session, sample_data):
    user = User(email="buyer@test.dev", password_hash="hash")
    db_session.add(user)
    await db_session.flush()

    order = Order(
        user_id=user.id,
        status=OrderStatus.pending,
        total=1999,
        provider="stripe",
        payment_session_id="cs_test_paid_at",
    )
    db_session.add(order)
    await db_session.commit()

    before = datetime.now(UTC)
    result = await apply_payment(db_session, "cs_test_paid_at")
    after = datetime.now(UTC)

    assert result is not None
    assert result.status == OrderStatus.paid
    assert result.paid_at is not None

    paid_at = result.paid_at
    if paid_at.tzinfo is None:
        paid_at = paid_at.replace(tzinfo=UTC)
    assert before <= paid_at <= after
