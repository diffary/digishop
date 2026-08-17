import asyncio

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=5, retry_backoff=True)
def deliver_order(self, order_id: int) -> None:
    # импорты внутри — чтобы monkeypatch app.services.delivery.deliver работал в тестах
    from app.core.db import fresh_session
    from app.services.delivery import deliver

    async def _run() -> None:
        async with fresh_session() as session:
            await deliver(session, order_id)

    try:
        asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
