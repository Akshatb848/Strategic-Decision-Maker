"""
BaseMCP — shared retry + timeout logic for all MCP tool wrappers.
"""

from __future__ import annotations

import asyncio
from typing import Any

from ..config import get_logger, get_settings

settings = get_settings()
logger = get_logger(__name__)

_FALLBACK_RESULT = "DATA_UNAVAILABLE: External data source could not be reached."


class BaseMCP:
    """Base class providing retry, timeout, and fallback for MCP tool calls."""

    source_name: str = "base"

    async def _call_with_retry(
        self,
        coro_fn: Any,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """
        Execute an async coroutine function with timeout and retry.
        On all failures, returns the fallback string instead of raising.
        """
        last_error: Exception | None = None

        for attempt in range(settings.mcp_retry_count + 1):
            try:
                result = await asyncio.wait_for(
                    coro_fn(*args, **kwargs),
                    timeout=settings.mcp_tool_timeout_seconds,
                )
                return result if result else _FALLBACK_RESULT
            except asyncio.TimeoutError as exc:
                last_error = exc
                logger.warning(
                    "mcp_timeout",
                    source=self.source_name,
                    attempt=attempt,
                    timeout=settings.mcp_tool_timeout_seconds,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "mcp_error",
                    source=self.source_name,
                    attempt=attempt,
                    error=str(exc),
                )
            if attempt < settings.mcp_retry_count:
                await asyncio.sleep(2**attempt)  # exponential backoff: 1s, 2s

        logger.error(
            "mcp_all_retries_failed",
            source=self.source_name,
            error=str(last_error),
        )
        return _FALLBACK_RESULT
