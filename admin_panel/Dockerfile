FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
RUN DJANGO_SECRET_KEY=build-only uv run --no-sync python manage.py collectstatic --noinput
EXPOSE 8001
ENTRYPOINT ["./docker-entrypoint.sh"]
