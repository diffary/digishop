from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, SessionDep
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, session: SessionDep) -> User:
    existing = await session.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(email=data.email, password_hash=hash_password(data.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    await session.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, session: SessionDep) -> TokenOut:
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    user = await session.scalar(select(User).where(User.email == data.email))
    if user is None or user.password_hash is None or not verify_password(
        data.password, user.password_hash
    ):
        raise invalid
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
