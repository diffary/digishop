from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import auth, downloads, health, oauth, orders, products, webhooks
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.redis import close_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await close_redis_client()


def create_app() -> FastAPI:
    app = FastAPI(title="DigiShop API", lifespan=lifespan)
    # это ЕДИНСТВЕННАЯ кука проекта — временная state-кука OAuth-редиректа (спека §5)
    app.add_middleware(SessionMiddleware, secret_key=get_settings().jwt_secret, max_age=300)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(oauth.router)
    app.include_router(products.router)
    app.include_router(orders.router)
    app.include_router(downloads.router)
    app.include_router(webhooks.router)
    register_error_handlers(app)
    # CORS для фронтенда: добавляем ПОСЛЕДНИМ, чтобы middleware стал самым внешним —
    # иначе заголовки CORS не попадают в ответы об ошибках (в т.ч. от register_error_handlers),
    # и браузер не сможет прочитать даже 4xx/5xx ответ с другого origin.
    # allow_credentials не включаем: куки в проекте не используются (спека §5, единственная
    # кука — временная state-кука OAuth-редиректа, к CORS-запросам фронтенда отношения не имеет).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[get_settings().frontend_url],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()
