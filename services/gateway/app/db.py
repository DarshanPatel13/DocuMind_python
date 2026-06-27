"""The gateway's tiny `users` table (login credentials only).

Owned solely by the gateway. We seed one demo user on startup so the app is
usable out of the box; in a real system this would be a full user service or an
external IdP (Keycloak/Auth0) — see docs/adr/0001 "next steps".
"""
from __future__ import annotations

from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings
from app.security import hash_password

engine = create_async_engine(settings.sqlalchemy_async_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(128), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)


async def init_db() -> None:
    """Create the users table and seed the demo user if it doesn't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        existing = await session.get(User, settings.demo_username)
        if existing is None:
            session.add(
                User(
                    username=settings.demo_username,
                    password_hash=hash_password(settings.demo_password),
                )
            )
            await session.commit()


async def get_user(username: str) -> User | None:
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
