"""Регистрация Celery-задач.

Явные импорты будущих модулей задач подключаются здесь, а не через
autodiscover (autodiscover_tasks ищет только tasks.py и тихо пропустил бы
наши модули app.tasks.delivery / app.tasks.maintenance).

Задачи 5-7 добавят сюда, например:
    from app.tasks import delivery  # noqa
    from app.tasks import maintenance  # noqa
"""

from app.tasks import delivery  # noqa: F401
