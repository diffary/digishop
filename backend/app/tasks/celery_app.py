from celery import Celery

from app.core.config import get_settings

celery_app = Celery("digishop", broker=get_settings().redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,  # fire-and-forget: без result backend — меньше команд Redis (лимиты Upstash)
    task_ignore_result=True,
    timezone="UTC",
    broker_transport_options={"health_check_interval": 120},
    broker_connection_retry_on_startup=True,
)
celery_app.autodiscover_tasks(["app.tasks"])


@celery_app.task
def ping() -> str:
    return "pong"
