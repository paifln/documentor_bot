from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings


def str_enum_column(enum_cls: type[PyEnum], **kwargs: Any) -> SAEnum:
    """SQLAlchemy's Enum() defaults to persisting the Python member *name*
    (e.g. "USER") rather than its *value* (e.g. "user") unless told
    otherwise. Every enum in this project is a StrEnum whose value is the
    lowercase string actually stored in Postgres (see Alembic migrations,
    which declare native enum types using the lowercase values) — so every
    Enum column MUST use values_callable, or inserts fail with
    'invalid input value for enum ...: "USER"'.
    """
    return SAEnum(enum_cls, values_callable=lambda cls: [e.value for e in cls], **kwargs)


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_async_engine(
        settings.database_url,
        echo=False,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = _make_engine()
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_models() -> None:
    """Create tables directly for local/dev/SQLite use. Production deployments
    should use Alembic migrations (see migrations/) instead of this."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-style dependency; also usable directly in bot handlers."""
    async with async_session_factory() as session:
        yield session
