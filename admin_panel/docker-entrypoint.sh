#!/bin/sh
set -e

uv run --no-sync python manage.py migrate --noinput

uv run --no-sync python manage.py createsuperuser --noinput || true

exec uv run --no-sync gunicorn config.wsgi:application --bind 0.0.0.0:8001
