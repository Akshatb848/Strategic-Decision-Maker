"""
ASIS v3.0 — Tavily web search MCP wrapper.
Provides structured web search results for market intelligence and competitor
analysis agents.  All failures return DATA_UNAVAILABLE — never raises.
"""
from __future__ import annotations

from typing import Any

from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings
from asis.backend.mcp.base_mcp import BaseMCP

logger = get_logger(__name__)


class WebSearchMCP(BaseMCP):
    """
    Wraps the Tavily search API with retry, timeout, and sanitisation.

    Usage
    -----
    mcp = WebSearchMCP()
    result = await mcp.search("AI chip market trends 2025", max_results=5)
    """

    source_name = "tavily_web_search"

    async def search(self, query: str, max_results: int = 5) -> str:
        """
        Execute a web search and return a formatted plain-text results string
        suitable for injection into an LLM prompt.

        Parameters
        ----------
        query : str
            Free-text search query.
        max_results : int
            Maximum number of results to return (default 5).

        Returns
        -------
        str
            Formatted search results, or DATA_UNAVAILABLE on failure.
        """
        return await self._call_with_retry(self._do_search, query, max_results=max_results)

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _do_search(self, query: str, max_results: int = 5) -> str:
        settings = get_settings()
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
    """Convert a raw Tavily response into a clean text block for LLM context."""
    lines: list[str] = []

    if answer := response.get("answer"):
        lines.append(f"Summary: {answer}\n")

    for i, result in enumerate(response.get("results", []), start=1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        snippet = (result.get("content") or "")[:500]
        lines.append(
            f"[{i}] {title}\n"
            f"    URL: {url}\n"
            f"    {snippet}\n"
        )

    return "\n".join(lines) or "No search results found."
