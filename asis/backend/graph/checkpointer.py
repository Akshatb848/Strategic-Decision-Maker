"""
ASIS v3.0 — PostgresSaver checkpointer for LangGraph 1.0.
Provides crash recovery and resumable analysis runs via Cloud SQL.
"""
from __future__ import annotations
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings

logger = get_logger(__name__)


async def get_checkpointer() -> Any:
    """
    Return an AsyncPostgresSaver instance connected to Cloud SQL.
    Falls back to MemorySaver if postgres unavailable (dev mode).
    """
    settings = get_settings()
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        # Convert asyncpg URL to psycopg URL for checkpointer
        db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
        await checkpointer.setup()
        logger.info("checkpointer_ready", backend="postgres")
        return checkpointer
    except Exception as exc:
        logger.warning("checkpointer_fallback", error=str(exc), backend="memory")
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
