import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models import DownloadLink, OrderItem, Product
from app.storage.base import Storage
from app.storage.local import get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/downloads", tags=["downloads"])

StorageDep = Annotated[Storage, Depends(get_storage)]


@router.get("/{token}")
async def download(token: str, session: SessionDep, storage: StorageDep) -> FileResponse:
    link = (
        await session.execute(select(DownloadLink).where(DownloadLink.token == token))
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Download not found")

    expires_at = link.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_410_GONE, "Download link expired")

    item = await session.get(OrderItem, link.order_item_id)
    product = await session.get(Product, item.product_id)

    try:
        file_exists = storage.exists(product.file_key)
    except ValueError:
        # traversal-образный ключ в БД — не 500, а 404 с логом (без токена: он ещё живой)
        logger.warning("download: rejected file_key %r (link_id=%s)", product.file_key, link.id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found") from None
    if not file_exists:
        logger.warning("download: file missing for key %s (link_id=%s)", product.file_key, link.id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")

    link.download_count += 1
    await session.commit()

    return FileResponse(
        storage.path(product.file_key),
        media_type="application/zip",
        filename=f"{product.slug}.zip",
    )
