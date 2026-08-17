"""Регистрация Celery-задач.

Модули задач подключаются явными импортами, а не через autodiscover:
autodiscover_tasks ищет только tasks.py и тихо пропустил бы
app.tasks.delivery / app.tasks.maintenance.
"""

from app.tasks import (
    delivery,  # noqa: F401
    maintenance,  # noqa: F401
)
