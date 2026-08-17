from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url)


_session_factory: async_sessionmaker[AsyncSession] | None = None


def session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory()() as session:
        yield session


@asynccontextmanager
async def fresh_session() -> AsyncIterator[AsyncSession]:
    """Сессия на СВЕЖЕМ движке — для Celery-задач.

    Каждый asyncio.run() в задаче создаёт новый event loop, а глобальный
    движок привязывается к лупу первой задачи процесса — вторая задача
    падает с «Future attached to a different loop» (поймано смоук-тестом).
    Здесь движок создаётся и гасится внутри текущего лупа.
    """
    engine = create_async_engine(get_settings().database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
