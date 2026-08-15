from app.tasks.celery_app import celery_app


@celery_app.task
def deliver_order(order_id: int) -> None:
    """Заглушка: реальная доставка (DownloadLink + Notification) — Task 6."""
