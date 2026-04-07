"""
Async SQLAlchemy session management.
Use get_db() as a FastAPI dependency in route handlers.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.db_echo,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a transactional async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. Called at application startup in non-production envs."""
    from .models import Base  # local import to avoid circular deps at module load

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def run_schema_migrations() -> None:
    """
    Idempotent schema migrations — safe to run on every startup.
    Uses ADD COLUMN IF NOT EXISTS so it's a no-op when columns already exist.
    """
    async with engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)")
        )
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS organization VARCHAR(255)")
        )


async def dispose_db() -> None:
    """Dispose engine connection pool. Called at application shutdown."""
    await engine.dispose()
