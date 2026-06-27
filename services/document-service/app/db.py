"""Async SQLAlchemy engine/session for the `documents` metadata table.

Vectors do NOT go through here — those are owned by the shared pgvector store
(documind_common.vector_store). This engine is metadata-only, kept async
(asyncpg) so it never blocks FastAPI's event loop.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.sqlalchemy_async_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for this service's ORM models."""


async def init_db() -> None:
    """Create the metadata tables at startup (idempotent)."""
    from app import models  # noqa: F401 — register models on Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session and always closes it."""
    async with SessionLocal() as session:
        yield session
