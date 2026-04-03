"""
MCP News Feed — NewsAPI wrapper.
Provides real-time news context for risk assessment and market intelligence.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from ..config import get_logger, get_settings
from .base_mcp import BaseMCP

settings = get_settings()
logger = get_logger(__name__)


class NewsFeedMCP(BaseMCP):
    """Wraps NewsAPI with retry and sanitisation."""

    source_name = "newsapi_feed"

    async def fetch(self, query: str, *, max_results: int = 5) -> str:
        """
        Fetch relevant news articles and return formatted string.
        Falls back to DATA_UNAVAILABLE on any error.
        """
        return await self._call_with_retry(self._do_fetch, query, max_results=max_results)

    async def _do_fetch(self, query: str, *, max_results: int = 5) -> str:
        api_key = settings.newsapi_key.get_secret_value()
        if not api_key:
            return "NEWS_FEED_UNAVAILABLE: NEWSAPI_KEY not configured."

        try:
            import httpx
        except ImportError:
            return "NEWS_FEED_UNAVAILABLE: httpx package not installed."

        from_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "from": from_date,
                    "sortBy": "relevancy",
                    "pageSize": max_results,
                    "language": "en",
                    "apiKey": api_key,
                },
            )
            response.raise_for_status()
            data = response.json()

        return _format_articles(data)


def _format_articles(data: dict) -> str:
    """Convert raw NewsAPI response into clean text for LLM context."""
    lines: list[str] = []
    for i, article in enumerate(data.get("articles", []), start=1):
        published = article.get("publishedAt", "")[:10]
        lines.append(
            f"[{i}] {article.get('title', 'Untitled')} ({published})\n"
            f"    Source: {article.get('source', {}).get('name', 'Unknown')}\n"
            f"    {article.get('description', '')}\n"
        )
    return "\n".join(lines) or "No news articles found."
