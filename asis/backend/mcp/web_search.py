"""
MCP Web Search — Tavily API wrapper.
Provides structured web search results for market intelligence and competitor analysis.
"""

from __future__ import annotations

import json
from typing import Any

from ..config import get_logger, get_settings
from .base_mcp import BaseMCP

settings = get_settings()
logger = get_logger(__name__)


class WebSearchMCP(BaseMCP):
    """Wraps Tavily search API with retry and sanitisation."""

    source_name = "tavily_web_search"

    async def search(self, query: str, *, max_results: int = 5) -> str:
        """
        Execute a web search and return formatted results string.
        Falls back to DATA_UNAVAILABLE on any error.
        """
        return await self._call_with_retry(self._do_search, query, max_results=max_results)

    async def _do_search(self, query: str, *, max_results: int = 5) -> str:
        api_key = settings.tavily_api_key.get_secret_value()
        if not api_key:
            return "WEB_SEARCH_UNAVAILABLE: TAVILY_API_KEY not configured."

        try:
            from tavily import AsyncTavilyClient  # type: ignore[import]
        except ImportError:
            return "WEB_SEARCH_UNAVAILABLE: tavily-python package not installed."

        client = AsyncTavilyClient(api_key=api_key)
        response = await client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
        )

        return _format_search_results(response)


def _format_search_results(response: dict[str, Any]) -> str:
    """Convert raw Tavily response into a clean text block for LLM context."""
    lines: list[str] = []

    if answer := response.get("answer"):
        lines.append(f"Summary: {answer}\n")

    for i, result in enumerate(response.get("results", []), start=1):
        lines.append(
            f"[{i}] {result.get('title', 'Untitled')}\n"
            f"    URL: {result.get('url', '')}\n"
            f"    {result.get('content', '')[:500]}\n"
        )

    return "\n".join(lines) or "No results found."
