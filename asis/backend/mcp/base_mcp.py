"""
ASIS v3.0 — BaseMCP: shared retry + timeout logic for all MCP wrappers.
All failures return DATA_UNAVAILABLE string — never raise exceptions.
"""
from __future__ import annotations
import asyncio
from typing import Any
from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings

logger = get_logger(__name__)
_FALLBACK = "DATA_UNAVAILABLE: external data source unreachable"


class BaseMCP:
    """
    Base class providing retry, timeout, and fallback for all MCP tool calls.

    Subclasses should:
      - Set ``source_name`` class attribute for log context.
      - Implement public async methods that delegate to ``_call_with_retry``.
      - Never let exceptions escape public methods.
    """

    source_name: str = "base"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._timeout = self._settings.mcp_tool_timeout_seconds
        self._retries = self._settings.mcp_retry_count

    async def _call_with_retry(self, coro_fn, *args: Any, **kwargs: Any) -> Any:
        """
        Execute an async coroutine function with timeout and exponential-backoff
        retry.  On all failures, returns the DATA_UNAVAILABLE fallback string
        instead of raising.

        Parameters
        ----------
        coro_fn : callable
            An async callable.  Called as ``coro_fn(*args, **kwargs)``.
        *args, **kwargs :
            Forwarded to *coro_fn*.

        Returns
        -------
        Any
            The result of *coro_fn* on success, or ``_FALLBACK`` on failure.
        """
        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                return await asyncio.wait_for(
                    coro_fn(*args, **kwargs),
                    timeout=self._timeout,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "mcp_retry",
                    attempt=attempt,
                    error=str(exc),
                    tool=self.__class__.__name__,
                    source=self.source_name,
                )
                if attempt < self._retries:
                    await asyncio.sleep(2 ** attempt)  # 1 s, 2 s, …

        logger.error(
            "mcp_failed",
            tool=self.__class__.__name__,
            source=self.source_name,
            error=str(last_exc),
        )
        return _FALLBACK
