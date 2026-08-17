import asyncio

from app.tasks.celery_app import celery_app


# retry_backoff работает ТОЛЬКО в паре с autoretry_for — при ручном self.retry()
# Celery молча использует фиксированный default_retry_delay (находка финального ревью)
@celery_app.task(autoretry_for=(Exception,), max_retries=5, retry_backoff=True)
def deliver_order(order_id: int) -> None:
    # импорты внутри — чтобы monkeypatch app.services.delivery.deliver работал в тестах
    from app.core.db import fresh_session
    from app.services.delivery import deliver

    async def _run() -> None:
        async with fresh_session() as session:
            await deliver(session, order_id)

    asyncio.run(_run())
