from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUser, SessionDep
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit())],
)
async def register(data: RegisterIn, session: SessionDep) -> User:
    email = data.email.lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # bcrypt нарочно медленный — в thread pool, чтобы не морозить event loop.
    password_hash = await run_in_threadpool(hash_password, data.password)
    user = User(email=email, password_hash=password_hash)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenOut, dependencies=[Depends(rate_limit())])
async def login(data: LoginIn, session: SessionDep) -> TokenOut:
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    email = data.email.lower()
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or user.password_hash is None:
        raise invalid
    # bcrypt нарочно медленный — в thread pool, чтобы не морозить event loop.
    if not await run_in_threadpool(verify_password, data.password, user.password_hash):
        raise invalid
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
