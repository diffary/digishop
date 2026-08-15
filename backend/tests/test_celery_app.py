from app.tasks.celery_app import celery_app, ping


def test_celery_app_configured():
    assert celery_app.conf.task_ignore_result is True
    assert celery_app.conf.result_backend is None


def test_ping_apply_runs_locally():
    assert ping.apply().get() == "pong"
