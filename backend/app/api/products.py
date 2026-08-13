from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.schemas.catalog import CategoryOut, ProductOut
from app.services import catalog as catalog_service

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(session: SessionDep) -> list[CategoryOut]:
    return await catalog_service.list_categories(session)


@router.get("/products", response_model=list[ProductOut])
async def list_products(
    session: SessionDep,
    category: str | None = None,
    search: str | None = None,
) -> list[ProductOut]:
    return await catalog_service.list_products(session, category, search)


@router.get("/products/{slug}", response_model=ProductOut)
async def get_product(slug: str, session: SessionDep) -> ProductOut:
    product = await catalog_service.get_product(session, slug)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product
