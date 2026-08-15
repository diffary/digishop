from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, health, orders, products, webhooks
from app.core.errors import register_error_handlers
from app.core.redis import close_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await close_redis_client()


def create_app() -> FastAPI:
    app = FastAPI(title="DigiShop API", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(products.router)
    app.include_router(orders.router)
    app.include_router(webhooks.router)
    register_error_handlers(app)
    return app


app = create_app()
