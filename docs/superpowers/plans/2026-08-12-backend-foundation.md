# DigiShop Backend Foundation — Implementation Plan (План 1 из 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Работающий бэкенд-фундамент DigiShop: FastAPI + async SQLAlchemy + Alembic + JWT-auth + каталог с Redis-кэшем и rate-limiting, поднимаемый через docker-compose, с тестами и CI.

**Architecture:** Слоёный FastAPI-бэкенд (api → services → models) по спеке `docs/superpowers/specs/2026-08-12-digishop-design.md` §3–§6. В этом плане НЕТ Stripe/Celery/OAuth (план 2) и фронтенда (план 3). Тесты бегут на SQLite (aiosqlite) + fakeredis — без сети и внешних сервисов.

**Tech Stack:** Python 3.12 (не 3.14 — у SQLAlchemy/celery-экосистемы поддержка отстаёт), uv, FastAPI, SQLAlchemy 2 async, Alembic, asyncpg, PyJWT, bcrypt, redis-py, pytest + pytest-asyncio + httpx + fakeredis, ruff, docker-compose.

**Условные обозначения:** все пути от корня репо `D:\files\digishop`. Все команды бэкенда выполняются из `backend/`. Python-команды — через `uv run`.

---

### Task 1: Скаффолд backend + /health

**Files:**
- Create: `backend/pyproject.toml`, `backend/.env.example`, `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/api/__init__.py`, `backend/app/api/health.py`, `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_health.py`, `.gitignore`

- [ ] **Step 1: Создать pyproject и окружение**

`backend/pyproject.toml`:

```toml
[project]
name = "digishop-backend"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic-settings>=2.4",
    "pyjwt>=2.9",
    "bcrypt>=4.2",
    "redis>=5.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
    "aiosqlite>=0.20",
    "fakeredis>=2.24",
    "ruff>=0.6",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

`.gitignore` (корень): стандартный Python + Node (`.venv/`, `__pycache__/`, `.env`, `node_modules/`, `dist/`).

`backend/.env.example`:

```
DATABASE_URL=postgresql+asyncpg://digishop:digishop@localhost:5432/digishop
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=change-me
```

Run: `cd backend && uv python pin 3.12 && uv sync`
Expected: создан `.venv`, lock-файл, зависимости встали.

- [ ] **Step 2: Написать падающий тест**

`backend/tests/conftest.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

`backend/tests/test_health.py`:

```python
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

Run: `uv run pytest tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: app.main`

- [ ] **Step 3: Реализовать app factory**

`backend/app/api/health.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

`backend/app/main.py`:

```python
from fastapi import FastAPI

from app.api import health


def create_app() -> FastAPI:
    app = FastAPI(title="DigiShop API")
    app.include_router(health.router)
    return app


app = create_app()
```

- [ ] **Step 4: Прогнать тест**

Run: `uv run pytest -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(backend): scaffold FastAPI app with /health"
```

---

### Task 2: docker-compose (postgres + redis + api)

**Files:**
- Create: `backend/Dockerfile`, `docker-compose.yml`

- [ ] **Step 1: Dockerfile**

`backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: docker-compose.yml (корень репо)**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: digishop
      POSTGRES_PASSWORD: digishop
      POSTGRES_DB: digishop
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U digishop"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  api:
    build: ./backend
    env_file: backend/.env
    environment:
      DATABASE_URL: postgresql+asyncpg://digishop:digishop@postgres:5432/digishop
      REDIS_URL: redis://redis:6379/0
    ports: ["8000:8000"]
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_started}

volumes:
  pgdata:
```

Примечание: сервисы `worker` и `beat` добавит план 2 (Celery) — компоуз дорастёт до 5 сервисов.

- [ ] **Step 3: Проверить**

Run: `cp backend/.env.example backend/.env && docker compose up -d --build && curl http://localhost:8000/health`
Expected: `{"status":"ok"}`

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: docker-compose with postgres, redis, api"
```

---

### Task 3: Конфиг и подключение к БД

**Files:**
- Create: `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/app/core/db.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Падающий тест**

`backend/tests/test_config.py`:

```python
from app.core.config import Settings


def test_settings_read_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "s3cret")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    s = Settings()
    assert s.jwt_secret == "s3cret"
```

Run: `uv run pytest tests/test_config.py -v` → FAIL (нет модуля)

- [ ] **Step 2: Реализация**

`backend/app/core/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`backend/app/core/db.py`:

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine():
    return create_async_engine(get_settings().database_url)


_session_factory: async_sessionmaker[AsyncSession] | None = None


def session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory()() as session:
        yield session
```

- [ ] **Step 3: Тесты зелёные** — `uv run pytest -v` → all passed

- [ ] **Step 4: Commit** — `git commit -am "feat(backend): settings and async db session"`

---

### Task 4: Модели и Alembic

**Files:**
- Create: `backend/app/models/__init__.py`, `backend/app/models/user.py`, `backend/app/models/catalog.py`, `backend/app/models/order.py`, `backend/alembic.ini`, `backend/alembic/env.py`, миграция
- Test: `backend/tests/test_models.py`

Модели строго по спеке §3. Все `price`/`total` — `Integer` (центы). Статусы заказа — `enum OrderStatus(str, Enum): pending/paid/delivered/failed`.

- [ ] **Step 1: Падающий тест**

`backend/tests/test_models.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.db import Base
from app.models import Category, DownloadLink, Notification, Order, OrderItem, Product, User


async def test_all_tables_create():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    names = set(Base.metadata.tables)
    assert names == {
        "users", "categories", "products",
        "orders", "order_items", "download_links", "notifications",
    }
```

Run → FAIL (нет моделей)

- [ ] **Step 2: Реализовать модели**

`backend/app/models/user.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(128))  # None у Google-пользователей
    google_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

`backend/app/models/catalog.py` — Category (id, name, slug unique) и Product (id, category_id FK, name, slug unique, description Text, price Integer, image_url, file_key, is_active default True).

`backend/app/models/order.py` — OrderStatus (str-enum), Order (id, user_id FK, status default pending, total Integer, provider String default "stripe", payment_session_id String nullable index, created_at), OrderItem (id, order_id FK, product_id FK, price_at_purchase Integer), DownloadLink (id, order_item_id FK, token String(36) unique default uuid4-hex, expires_at DateTime, download_count Integer default 0), Notification (id, user_id FK, order_id FK, type String, payload JSON, created_at).

`backend/app/models/__init__.py` реэкспортирует все модели.

- [ ] **Step 3: Тест зелёный** — `uv run pytest tests/test_models.py -v` → PASS

- [ ] **Step 4: Alembic**

Run: `uv run alembic init alembic`
В `alembic/env.py`: target_metadata = `Base.metadata`, url из `Settings` (sync-вариант: заменить `+asyncpg` на пустую строку не надо — использовать async engine template: `uv run alembic init -t async alembic`). Использовать **async-шаблон**.
Run: `uv run alembic revision --autogenerate -m "initial schema"` (нужен запущенный postgres из compose)
Run: `uv run alembic upgrade head`
Expected: 7 таблиц в postgres (`docker compose exec postgres psql -U digishop -c '\dt'`)

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat(backend): models and initial alembic migration"`

---

### Task 5: Auth (register / login / me)

**Files:**
- Create: `backend/app/core/security.py`, `backend/app/schemas/__init__.py`, `backend/app/schemas/auth.py`, `backend/app/api/auth.py`, `backend/app/api/deps.py`
- Modify: `backend/app/main.py` (include router)
- Test: `backend/tests/test_auth.py`, расширить `backend/tests/conftest.py`

- [ ] **Step 1: Тестовая инфраструктура — БД-фикстура**

Дополнить `conftest.py`: engine на `sqlite+aiosqlite://` (in-memory, StaticPool), `Base.metadata.create_all`, переопределение зависимости `get_session` через `app.dependency_overrides`. Env-переменные для Settings задаются в `conftest.py` через `os.environ.setdefault` (JWT_SECRET=test и т.д.) до импорта app.

- [ ] **Step 2: Падающие тесты**

`backend/tests/test_auth.py`:

```python
async def test_register_and_login(client):
    r = await client.post("/auth/register", json={"email": "a@b.c", "password": "pass1234"})
    assert r.status_code == 201

    r = await client.post("/auth/login", json={"email": "a@b.c", "password": "pass1234"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.c"


async def test_register_duplicate_email(client):
    await client.post("/auth/register", json={"email": "a@b.c", "password": "pass1234"})
    r = await client.post("/auth/register", json={"email": "a@b.c", "password": "other123"})
    assert r.status_code == 409


async def test_login_wrong_password(client):
    await client.post("/auth/register", json={"email": "a@b.c", "password": "pass1234"})
    r = await client.post("/auth/login", json={"email": "a@b.c", "password": "wrong"})
    assert r.status_code == 401


async def test_me_without_token(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401
```

Run → FAIL (404)

- [ ] **Step 3: Реализация**

`app/core/security.py`: `hash_password`/`verify_password` (bcrypt), `create_access_token(user_id) -> str` и `decode_token(token) -> int` (PyJWT, `exp` по настройке, `sub=str(user_id)`).

`app/api/deps.py`: `get_current_user` — достаёт Bearer-токен (`fastapi.security.HTTPBearer(auto_error=False)`), decode, грузит User из БД, иначе 401.

`app/api/auth.py`: POST `/auth/register` (409 на дубль email, минимум 8 символов пароля через Pydantic), POST `/auth/login` (401 одинаковый и для «нет юзера», и для «не тот пароль» — не раскрываем существование email), GET `/auth/me`.

Подключить router в `create_app`.

- [ ] **Step 4: Зелёные тесты** — `uv run pytest -v` → all passed

- [ ] **Step 5: Commit** — `git commit -am "feat(backend): email+password auth with JWT"`

---

### Task 6: Каталог + seed

**Files:**
- Create: `backend/app/schemas/catalog.py`, `backend/app/services/__init__.py`, `backend/app/services/catalog.py`, `backend/app/api/products.py`, `backend/scripts/seed.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_catalog.py`

- [ ] **Step 1: Падающие тесты**

`backend/tests/test_catalog.py` — фикстура `sample_data` пишет в тестовую сессию 2 категории и 3 товара (один `is_active=False`); тесты:

```python
async def test_list_products_excludes_inactive(client, sample_data): ...   # len == 2
async def test_filter_by_category(client, sample_data): ...               # ?category=slug
async def test_search_by_name(client, sample_data): ...                   # ?search=подстрока (ilike)
async def test_product_detail_by_slug(client, sample_data): ...           # /products/{slug}
async def test_product_detail_404(client): ...
async def test_list_categories(client, sample_data): ...
```

Run → FAIL

- [ ] **Step 2: Реализация**

`services/catalog.py`: `list_products(session, category_slug, search)`, `get_product(session, slug)`, `list_categories(session)`. Фильтр только `is_active=True`, поиск `Product.name.ilike(f"%{search}%")`.

`api/products.py`: GET `/categories`, GET `/products`, GET `/products/{slug}`. Схемы ответов в `schemas/catalog.py` (`ProductOut`: id, name, slug, description, price, image_url, category_slug — **без** `file_key`, путь к файлу наружу не отдаём).

`scripts/seed.py`: идемпотентный скрипт (upsert по slug) — 3 категории, 9 демо-товаров. Запуск: `uv run python -m scripts.seed`.

- [ ] **Step 3: Зелёные тесты**, seed проверить на compose-postgres: `uv run python -m scripts.seed && curl "http://localhost:8000/products" | head -c 300`

- [ ] **Step 4: Commit** — `git commit -am "feat(backend): catalog endpoints and seed script"`

---

### Task 7: Redis — кэш каталога

**Files:**
- Create: `backend/app/core/redis.py`, `backend/app/services/cache.py`
- Modify: `backend/app/api/products.py`, `backend/tests/conftest.py` (fakeredis fixture + override)
- Test: `backend/tests/test_cache.py`

- [ ] **Step 1: Падающие тесты**

```python
async def test_products_response_is_cached(client, sample_data, fake_redis):
    await client.get("/products")
    keys = await fake_redis.keys("cache:products:*")
    assert keys

async def test_cache_key_varies_by_query(client, sample_data, fake_redis): ...
async def test_cache_hit_skips_db(client, sample_data, fake_redis, monkeypatch): ...
    # второй запрос: monkeypatch list_products -> raise AssertionError; ответ всё равно 200 из кэша
```

Run → FAIL

- [ ] **Step 2: Реализация**

`core/redis.py`: `get_redis()` — singleton `redis.asyncio.Redis.from_url(settings.redis_url, decode_responses=True)`; в тестах подменяется на fakeredis через dependency override / фикстуру.

`services/cache.py`:

```python
import json

CATALOG_TTL = 300  # 5 минут по спеке §6


async def get_or_set(redis, key: str, ttl: int, loader):
    cached = await redis.get(key)
    if cached is not None:
        return json.loads(cached)
    value = await loader()
    await redis.set(key, json.dumps(value), ex=ttl)
    return value


async def invalidate_catalog(redis):
    keys = [k async for k in redis.scan_iter("cache:products:*")]
    if keys:
        await redis.delete(*keys)
```

В `api/products.py` list/detail оборачиваются в `get_or_set` с ключами `cache:products:list:{category}:{search}` и `cache:products:detail:{slug}`. `invalidate_catalog` вызывается из seed-скрипта после записи (и позже — из Django-админки этапа 2 это опишет отдельный план).

- [ ] **Step 3: Зелёные тесты** — `uv run pytest -v`

- [ ] **Step 4: Commit** — `git commit -am "feat(backend): redis cache for catalog with TTL"`

---

### Task 8: Rate limiting на auth

**Files:**
- Create: `backend/app/core/rate_limit.py`
- Modify: `backend/app/api/auth.py`
- Test: `backend/tests/test_rate_limit.py`

- [ ] **Step 1: Падающий тест**

```python
async def test_login_rate_limited(client, fake_redis):
    for _ in range(10):
        await client.post("/auth/login", json={"email": "x@y.z", "password": "wrong123"})
    r = await client.post("/auth/login", json={"email": "x@y.z", "password": "wrong123"})
    assert r.status_code == 429
```

Run → FAIL (401, а не 429)

- [ ] **Step 2: Реализация**

`core/rate_limit.py` — фиксированное окно на Redis `INCR` + `EXPIRE`: зависимость `rate_limit(limit=10, window_sec=60)`, ключ `rl:{route}:{client_ip}` (ip из `request.client.host`). Ответ 429 с `Retry-After`. Повесить на `/auth/login` и `/auth/register`.

- [ ] **Step 3: Зелёные тесты**, полный прогон: `uv run pytest -v` → all passed, ruff чистый: `uv run ruff check .`

- [ ] **Step 4: Commit** — `git commit -am "feat(backend): redis rate limiting on auth endpoints"`

---

### Task 9: CI (GitHub Actions)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Workflow**

```yaml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    defaults: {run: {working-directory: backend}}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run pytest -v
        env:
          DATABASE_URL: sqlite+aiosqlite://
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET: ci-secret
      - run: docker build -t digishop-api .
```

(фронтенд-job добавит план 3)

- [ ] **Step 2: Локальная проверка эквивалента** — `uv run ruff check . && uv run pytest -v` → чисто

- [ ] **Step 3: Commit** — `git add -A && git commit -m "ci: backend lint, tests, docker build"`

---

## Критерий завершения плана 1

- `docker compose up` поднимает postgres+redis+api, `/health` отвечает, seed наполняет каталог, `/products` отдаёт товары (и кэширует в Redis).
- `uv run pytest -v` — все зелёные; ruff чистый.
- Все коммиты на месте.
- Следующий шаг — план 2: Stripe + Celery + OAuth (пишется после завершения этого).
