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
    Covers columns added by ORM model evolution that aren't in migration 0001.
    """
    async with engine.begin() as conn:
        # ── users ─────────────────────────────────────────────────────────────
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)")
        )
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS organization VARCHAR(255)")
        )
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id UUID")
        )
        await conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) "
                "NOT NULL DEFAULT 'analyst'"
            )
        )

        # ── analyses ──────────────────────────────────────────────────────────
        await conn.execute(
            text("ALTER TABLE analyses ADD COLUMN IF NOT EXISTS tenant_id UUID")
        )
        await conn.execute(
            text(
                "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS trigger_source VARCHAR(50) "
                "NOT NULL DEFAULT 'api'"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS checkpoint_thread_id VARCHAR(100)"
            )
        )

        # ── agent_runs ────────────────────────────────────────────────────────
        await conn.execute(
            text("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS tenant_id UUID")
        )
        await conn.execute(
            text("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS tokens_cost_usd FLOAT")
        )
        await conn.execute(
            text(
                "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS rag_hits INTEGER "
                "NOT NULL DEFAULT 0"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS memory_hit BOOLEAN "
                "NOT NULL DEFAULT false"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS langfuse_trace_id VARCHAR(100)"
            )
        )

        # ── reports ───────────────────────────────────────────────────────────
        # This is the critical one: ORM model has tenant_id NOT NULL but
        # migration 0001 created reports without it → every Report INSERT fails.
        await conn.execute(
            text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS tenant_id UUID")
        )
        await conn.execute(
            text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS exported_at TIMESTAMPTZ")
        )


async def dispose_db() -> None:
    """Dispose engine connection pool. Called at application shutdown."""
    await engine.dispose()
