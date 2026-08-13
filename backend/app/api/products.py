from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import SessionDep
from app.core.redis import get_redis
from app.schemas.catalog import CategoryOut, ProductOut
from app.services import catalog as catalog_service
from app.services.cache import CATALOG_TTL, get_or_set
from app.services.catalog import get_product, list_products

router = APIRouter(tags=["catalog"])

RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories_endpoint(session: SessionDep) -> list[CategoryOut]:
    return await catalog_service.list_categories(session)


@router.get("/products", response_model=list[ProductOut])
async def list_products_endpoint(
    session: SessionDep,
    redis: RedisDep,
    category: Annotated[str | None, Query(max_length=100)] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> list[ProductOut]:
    key = f"cache:products:list:{category or ''}:{search or ''}"

    async def loader() -> list[dict]:
        products = await list_products(session, category, search)
        return [p.model_dump() for p in products]

    return await get_or_set(redis, key, CATALOG_TTL, loader)


@router.get("/products/{slug}", response_model=ProductOut)
async def get_product_endpoint(slug: str, session: SessionDep, redis: RedisDep) -> ProductOut:
    key = f"cache:products:detail:{slug}"

    async def loader() -> dict:
        product = await get_product(session, slug)
        if product is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
        return product.model_dump()

    return await get_or_set(redis, key, CATALOG_TTL, loader)
