import logging
import secrets
from typing import Annotated

import redis.asyncio as aioredis
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.redis import get_redis
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import TokenOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["oauth"])

RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]

oauth = OAuth()
oauth.register(
    "google",
    client_id=get_settings().google_client_id or None,
    client_secret=get_settings().google_client_secret or None,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email"},
)


class ExchangeIn(BaseModel):
    code: str


@router.get("/google")
async def google_login(request: Request):
    redirect_uri = f"{get_settings().backend_url}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, session: SessionDep, redis: RedisDep):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as exc:
        # отказ на экране Google / битый state — действие пользователя, не наша авария
        logger.info("Google OAuth aborted: %s", exc.error)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OAuth flow was not completed") from None

    info = token["userinfo"]
    # доверяем email только если Google его верифицировал — иначе привязка
    # по email была бы вектором захвата чужого аккаунта
    if not info.get("email_verified", False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google account email is not verified")
    email = info["email"].lower()
    google_id = info["sub"]

    user = await session.scalar(select(User).where(User.google_id == google_id))
    if user is None:
        user = await session.scalar(select(User).where(User.email == email))
        if user is not None:
            user.google_id = google_id
        else:
            user = User(email=email, google_id=google_id, password_hash=None)
            session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info("Google OAuth login for user_id=%s", user.id)

    code = secrets.token_urlsafe(32)
    await redis.set(f"oauth:code:{code}", str(user.id), ex=60)

    frontend_url = get_settings().frontend_url
    return RedirectResponse(f"{frontend_url}/auth/callback?code={code}", status_code=302)


@router.post("/exchange", response_model=TokenOut)
async def exchange_code(data: ExchangeIn, redis: RedisDep) -> TokenOut:
    user_id = await redis.getdel(f"oauth:code:{data.code}")
    if user_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")
    return TokenOut(access_token=create_access_token(int(user_id)))
