# DigiShop Payments & Background Jobs — Implementation Plan (План 2 из 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Полный платёжный флоу: заказ → Stripe Checkout (test mode) → вебхук → Celery-доставка (ссылки на скачивание + Notification) → скачивание по токену; плюс Google OAuth и единый формат ошибок. docker-compose дорастает до 5 сервисов.

**Architecture:** По спеке §2, §4–§6. Платежи за абстракцией `PaymentProvider` (Stripe сегодня, LiqPay потом). Вебхук: подпись → идемпотентный переход `pending→paid` → постановка Celery-задачи → быстрый 200. Celery-задачи синхронные, внутри — `asyncio.run()` вокруг async-логики (переиспользуем существующие async-сервисы). Тесты: Stripe и Google мокаются, Celery в eager-режиме, Redis — fakeredis; сеть не нужна.

**Tech Stack:** stripe (SDK), celery[redis], authlib, httpx; остальное уже в проекте.

**Правила исполнителям:** `app/core/security.py` и `app/services/cache.py` написаны пользователем — НЕ трогать. Коммитить только именованные файлы (никаких `git add -A`). Docker-проверки: если демон не запущен — пометить шаг как SKIPPED (daemon down) в отчёте, НЕ считать это блокером, тесты обязаны проходить без докера. Трейлер коммитов: пустая строка + `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Единый формат ошибок + глобальный exception handler

**Files:** Create `backend/app/core/errors.py`; Modify `backend/app/main.py`; Test `backend/tests/test_errors.py`

- [ ] Красные тесты: (1) несуществующий путь → 404 `{"detail": ...}`; (2) искусственный роут (регистрируется только в тесте через `app.include_router`), бросающий `RuntimeError` → 500 с телом РОВНО `{"detail": "Internal server error"}` (без утечки текста исключения) — использовать `client` с `raise_server_exceptions=False`-аналогом httpx: `ASGITransport(app, raise_app_exceptions=False)` в отдельной фикстуре.
- [ ] Реализация: `errors.py` — обработчик `Exception` → лог с трейсбеком (`logging.exception`) + JSON 500; регистрация в `create_app()`. HTTPException/валидация FastAPI уже дают `{"detail": ...}` — не переопределять.
- [ ] `uv run pytest -v` (32 passed), ruff+format чистые. Commit: `feat(backend): unified error format and global exception handler`

### Task 2: Celery-каркас + compose до 5 сервисов

**Files:** Create `backend/app/tasks/__init__.py`, `backend/app/tasks/celery_app.py`; Modify `backend/pyproject.toml` (deps: `celery[redis]>=5.4`, `stripe>=10`, `authlib>=1.3`), `docker-compose.yml`, `backend/.env.example`; Test `backend/tests/test_celery_app.py`

- [ ] Красный тест: celery_app импортируется; `ping.apply().get() == "pong"` (`apply()` выполняет задачу локально — БЕЗ autouse eager-фикстуры: глобальный eager-режим не нужен нигде в плане, задачи в тестах либо вызываются как обычные функции/через apply(), либо мокается `.delay`).
- [ ] `celery_app.py`:

```python
from celery import Celery

from app.core.config import get_settings

celery_app = Celery("digishop", broker=get_settings().redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,        # fire-and-forget: без result backend — меньше команд Redis (важно для лимитов Upstash)
    task_ignore_result=True,
    timezone="UTC",
)
celery_app.autodiscover_tasks(["app.tasks"])


@celery_app.task
def ping() -> str:
    return "pong"
```

Дополнительно в conf: `broker_transport_options={"health_check_interval": 120}` — вместе с отсутствием result backend и `--without-*` флагами это наша экономия команд Redis под лимиты Upstash (спека §2).

ВНИМАНИЕ: `get_settings()` на уровне модуля — здесь допустимо (воркер и API стартуют с готовым env), а в conftest env выставлен до импортов, так что тесты не ломаются. Autouse eager-фикстуру НЕ добавлять (см. Task 6 — стратегия тестирования задач без eager).

В deps добавить также `itsdangerous>=2.2` — нужен SessionMiddleware в Task 9 (authlib его не тянет, проверено ревью).
- [ ] compose: сервисы `worker` (`command: uv run --no-sync celery -A app.tasks.celery_app worker --loglevel=info --without-gossip --without-mingle --without-heartbeat`) и `beat` (`command: uv run --no-sync celery -A app.tasks.celery_app beat --loglevel=info`), оба `build: ./backend`, те же env, что api, `depends_on: redis`. Флаги `--without-*` — осознанная экономия команд Redis (Upstash-лимиты, спека §2).
- [ ] `.env.example` дополнить: `STRIPE_SECRET_KEY=sk_test_...`, `STRIPE_WEBHOOK_SECRET=whsec_...`, `FRONTEND_URL=http://localhost:5173`, `BACKEND_URL=http://localhost:8000`, `GOOGLE_CLIENT_ID=`, `GOOGLE_CLIENT_SECRET=`.
- [ ] Если докер запущен: `docker compose up -d --build` → 5 контейнеров, в логах worker'а "ready". Иначе SKIPPED.
- [ ] Тесты+линт зелёные (uv sync после правки pyproject). Commit: `feat(backend): celery skeleton and 5-service compose`

### Task 3: Settings + PaymentProvider абстракция + Stripe

**Files:** Create `backend/app/payments/__init__.py`, `backend/app/payments/base.py`, `backend/app/payments/stripe_provider.py`; Modify `backend/app/core/config.py`; Test `backend/tests/test_payments_provider.py`

- [ ] Settings: добавить `stripe_secret_key: str = ""`, `stripe_webhook_secret: str = ""`, `frontend_url: str = "http://localhost:5173"`, `backend_url: str = "http://localhost:8000"`, `google_client_id: str = ""`, `google_client_secret: str = ""` (дефолты пустые — тесты и локалка без Stripe-ключей не падают).
- [ ] `base.py`:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass
class CheckoutSession:
    session_id: str
    url: str


class PaymentProvider(Protocol):
    name: str

    async def create_checkout(self, *, order_id: int, amount_total: int, description: str) -> CheckoutSession: ...

    def verify_webhook(self, payload: bytes, signature: str) -> dict: ...
```

- [ ] `stripe_provider.py`: класс `StripeProvider` (name="stripe"); `create_checkout` — `stripe.checkout.Session.create` (mode="payment", одна line_item с amount_total в центах и description, `success_url=f"{settings.frontend_url}/order/success?order_id={order_id}"`, `cancel_url=.../order/cancel`, `metadata={"order_id": str(order_id)}`); stripe SDK синхронный — звать через `asyncio.to_thread`. `verify_webhook` — `stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)`; ВАЖНО (проверено ревью на stripe 15.x): исключение называется `stripe.SignatureVerificationError` (модуля `stripe.error` больше НЕТ — удалён в v8), его пробрасывать (ловит роут); `construct_event` возвращает `stripe.Event` — вернуть `event.to_dict_recursive()`, чтобы прод и моки (обычные dict) вели себя одинаково. Модульная функция `get_payment_provider() -> PaymentProvider` (пока всегда StripeProvider) — DI-точка для тестов.
- [ ] Тесты: провайдер мокается monkeypatch'ем на уровне stripe SDK (`stripe.checkout.Session.create` → фейковый объект с id/url; `stripe.Webhook.construct_event` → dict или raise) — проверить, что create_checkout передаёт правильные суммы/URL/metadata и что verify_webhook пробрасывает ошибку подписи.
- [ ] Зелёные, линт. Commit: `feat(backend): payment provider abstraction with stripe implementation`

### Task 4: Заказы — POST /orders + история

**Files:** Create `backend/app/schemas/orders.py`, `backend/app/services/orders.py`, `backend/app/api/orders.py`; Modify `backend/app/main.py`; Test `backend/tests/test_orders.py`

- [ ] Красные тесты (авторизованный клиент — фикстура `auth_client` в conftest: регистрирует юзера и ставит заголовок):
  - `POST /orders {"product_ids": [id1, id2]}` → 201 `{order_id, checkout_url}`; в БД Order(pending, total=сумма цен ИЗ БД) + 2 OrderItem с price_at_purchase; provider замокан через dependency override `get_payment_provider`.
  - Цены с фронта игнорируются по построению (в теле их просто нет) — тест: total == сумма актуальных цен БД.
  - Неактивный/несуществующий product_id → 422 с пояснением; пустой список → 422; дубликаты в списке схлопываются.
  - Без токена → 401.
  - `GET /orders` → список своих заказов (новые сверху) со статусом и items; чужие заказы не видны (создать второго юзера).
  - `GET /orders/{id}` → 200 свой / 404 чужой или несуществующий.
- [ ] Реализация: `services/orders.py::create_order(session, user, product_ids, provider)` — валидация товаров (активные, существуют), Order+OrderItems, flush → id, `provider.create_checkout(...)`, сохранить `payment_session_id=session_id`, commit, вернуть (order, url). Схемы: `OrderCreateIn(product_ids: list[int] = Field(min_length=1, max_length=50))`, `OrderOut`, `OrderItemOut`. Роутер `/orders` с `CurrentUser`.
- [ ] Для dependency override `get_payment_provider` нужен доступ к app: вынести в conftest отдельную фикстуру `app` (создание `create_app()` + оба существующих override), а `client` и новый `auth_client` строить поверх неё — НЕ лезть в приватные поля клиента.
- [ ] Зелёные, линт. Commit: `feat(backend): order creation with checkout and order history`

### Task 5: Stripe-вебхук (сердце проекта)

**Files:** Create `backend/app/api/webhooks.py`, `backend/app/services/payments_flow.py`, `backend/app/tasks/delivery.py` (ЗАГЛУШКА: no-op задача `deliver_order(order_id)` с docstring «реализация в Task 6» — нужна, чтобы вебхук мог её импортировать, а тесты — мокать `.delay`); Modify `backend/app/main.py`; Test `backend/tests/test_webhook.py`

**ПРОЦЕССНОЕ:** функция `apply_payment(session, payment_session_id) -> Order | None` в `payments_flow.py` — кандидат на ручное упражнение пользователя (как security.py/cache.py): исполнителю реализовать полностью и работоспособно, контроллер потом обнулит для упражнения.

- [ ] Красные тесты (самые важные тесты проекта):
  - валидный вебхук `checkout.session.completed` по pending-заказу → 200, заказ стал `paid`, и `deliver_order.delay` вызван с order.id (monkeypatch на `.delay` — так тесты вебхука остаются НАВСЕГДА: сквозной «до delivered» проверки через eager НЕ будет, см. Task 6);
  - повторный тот же вебхук → 200, но статус НЕ меняется повторно и задача НЕ ставится второй раз (идемпотентность);
  - неверная подпись (verify_webhook бросает) → 400;
  - вебхук по неизвестному `payment_session_id` → 200 с логом (Stripe нельзя отвечать 4xx на неизвестные события — он будет ретраить вечно);
  - событие другого типа (например `payment_intent.created`) → 200, ничего не происходит.
- [ ] Реализация: `POST /webhooks/stripe` — читает `await request.body()` и заголовок `stripe-signature`, `provider.verify_webhook` (SignatureVerificationError → 400), если `event["type"] == "checkout.session.completed"` — достать `session.id` → `apply_payment` → если вернул Order, поставить `deliver_order.delay(order.id)`. Всегда быстрый `{"status": "ok"}`.
- [ ] `apply_payment`: найти Order по payment_session_id; нет → None; статус != pending → None (идемпотентность); иначе `pending→paid`, commit, вернуть Order.
- [ ] Зелёные, линт. Commit: `feat(backend): stripe webhook with signature check and idempotent payment apply`

### Task 6: Celery-доставка + Notification

**Files:** Create `backend/app/tasks/delivery.py`, `backend/app/services/delivery.py`; Test `backend/tests/test_delivery.py`

- [ ] Красные тесты — стратегия БЕЗ eager (важно, ловушка найдена ревью: eager выполняет задачу в потоке вызывающего, а внутри задачи `asyncio.run()` — из async-теста с уже работающим event loop это RuntimeError, к тому же тестовый aiosqlite-движок привязан к лупу теста):
  1. **Бизнес-логика — напрямую через async-сервис** `deliver(session, order_id)` в обычных async-тестах: по paid-заказу создаёт DownloadLink на каждый OrderItem (expires_at = +7 дней) и Notification(type="order_delivered", payload с токенами), статус → `delivered`; повторный вызов по delivered — no-op (идемпотентность); по pending — no-op с warning-логом.
  2. **Celery-обёртка — одним СИНХРОННЫМ тестом** (def, не async): monkeypatch `app.services.delivery.deliver` на записывающий async-стаб → вызвать `deliver_order.run(42)` (или `.apply(args=[42])`) → стаб получил order_id=42. Здесь `asyncio.run` легален — снаружи нет запущенного лупа. БД не участвует.
- [ ] Реализация: `services/delivery.py::deliver(session, order_id)` — async-логика; `tasks/delivery.py`:

```python
import asyncio

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=5, retry_backoff=True)
def deliver_order(self, order_id: int) -> None:
    from app.core.db import session_factory
    from app.services.delivery import deliver

    async def _run() -> None:
        async with session_factory()() as session:
            await deliver(session, order_id)

    try:
        asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc)
```

Импорты session_factory/deliver — внутри функции задачи (как в сниппете): это осознанно, чтобы monkeypatch в синхронном тесте обёртки работал через `app.services.delivery.deliver`.
- [ ] Заглушку `deliver_order` из Task 5 заменить реальной реализацией. Тесты вебхука НЕ трогать — они мокают `.delay` и остаются как есть.
- [ ] Зелёные, линт. Commit: `feat(backend): celery order delivery with download links and notifications`

### Task 7: Периодика — beat-задачи

**Files:** Create `backend/app/tasks/maintenance.py`; Modify `backend/app/tasks/celery_app.py` (beat_schedule); Test `backend/tests/test_maintenance.py`

- [ ] Красные тесты: `expire_pending_orders` переводит pending старше 1 часа в failed (свежие не трогает); `cleanup_expired_links` удаляет DownloadLink с истёкшим expires_at (живые не трогает).
- [ ] Реализация: async-сервисы + celery-обёртки по образцу Task 6; `beat_schedule`: expire — каждые 15 минут, cleanup — раз в сутки.
- [ ] Зелёные, линт. Commit: `feat(backend): beat tasks for pending expiry and link cleanup`

### Task 8: Скачивание — Storage + GET /downloads/{token}

**Files:** Create `backend/app/storage/__init__.py`, `backend/app/storage/base.py`, `backend/app/storage/local.py`, `backend/app/api/downloads.py`, `backend/files/.gitkeep` + 1 демо-zip; Modify `backend/app/main.py`, `backend/scripts/seed.py` (file_key существующего демо-файла); Test `backend/tests/test_downloads.py`

- [ ] Красные тесты: валидный токен → 200 с файлом (FileResponse), download_count +1; истёкший → 410; несуществующий → 404; повторное скачивание валидным токеном работает (лимита нет — спека §3).
- [ ] Реализация: `Storage` Protocol (`exists(key) -> bool`, `path(key) -> Path`); `LocalStorage(root=<каталог backend/>)` — ВАЖНО: существующие file_key уже содержат префикс `files/` (seed и conftest sample_data), поэтому root — это `backend/`, а не `backend/files/`, иначе получится `files/files/...`; эндпоинт публичный (токен и есть секрет), безопасность: key приходит ТОЛЬКО из БД (file_key), не из URL — path traversal невозможен по построению, но в LocalStorage всё равно проверить `resolve().is_relative_to(root)`.
- [ ] Зелёные, линт. Commit: `feat(backend): token-based downloads with storage abstraction`

### Task 9: Google OAuth2

**Files:** Create `backend/app/api/oauth.py`; Modify `backend/app/main.py`, `backend/app/api/deps.py` (если нужно); Test `backend/tests/test_oauth.py`

- [ ] Красные тесты (authlib мокается — monkeypatch объекта oauth-клиента):
  - `GET /auth/google` → 302 на accounts.google.com (или мок-URL);
  - callback с моком userinfo (email+sub): новый email → создан User(google_id, password_hash=None); существующий email без google_id → google_id дописан; ответ — 302 на `{frontend_url}/auth/callback?code=<одноразовый>`;
  - `POST /auth/exchange {"code": ...}` → TokenOut (JWT работает с /auth/me); повторный exchange тем же кодом → 400 (одноразовость, код удалён из Redis); мусорный код → 400;
  - код в Redis живёт с TTL ≤ 60 сек (проверить ttl как в кэш-тестах).
- [ ] Реализация: authlib `OAuth().register("google", ...)` c `server_metadata_url="https://accounts.google.com/.well-known/openid-configuration"`; SessionMiddleware (нужен authlib для state-куки; `secret_key=settings.jwt_secret`, `max_age=300`) — это ЕДИНСТВЕННАЯ кука проекта, задокументировать комментарием со ссылкой на спеку §5. Callback: userinfo → find-or-create → `secrets.token_urlsafe(32)` → `redis.set(f"oauth:code:{code}", user_id, ex=60)` → redirect. Exchange: `GETDEL`-семантика (redis `getdel`) → JWT.
- [ ] Зелёные, линт. Commit: `feat(backend): google oauth with one-time code exchange`

### Task 10: Живой smoke-тест (вместе с пользователем — НЕ субагентская задача)

Контроллер + пользователь, когда докер включён и есть Stripe test-ключи:
- [ ] `docker compose up -d --build` — 5 сервисов живы.
- [ ] Stripe CLI: `stripe listen --forward-to localhost:8000/webhooks/stripe` → ключ whsec в .env.
- [ ] Полный флоу руками: register → POST /orders (через /docs) → оплата тестовой картой 4242… на странице Stripe → вебхук пришёл → worker доставил → GET /orders показывает delivered → скачать файл по токену.
- [ ] Google OAuth локально: завести OAuth Client в Google Cloud Console (redirect URI `http://localhost:8000/auth/google/callback`) — по желанию пользователя, можно отложить до деплоя.

## Критерий завершения плана 2

1. Все тесты зелёные (~55+), ruff check + format чистые, CI-эквивалент проходит без докера.
2. Идемпотентность вебхука и доставки покрыты тестами.
3. docker-compose: 5 сервисов (api, worker, beat, postgres, redis).
4. Живой smoke-тест (Task 10) пройден.
5. Ручное упражнение пользователя: `apply_payment` в payments_flow.py.
6. Obsidian-заметки: Celery, Stripe-вебхуки, OAuth2 — написаны контроллером по ходу.
