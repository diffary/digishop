from fastapi import FastAPI

from app.api import auth, health, products


def create_app() -> FastAPI:
    app = FastAPI(title="DigiShop API")
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(products.router)
    return app


app = create_app()
