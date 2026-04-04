"""
ASIS v3.0 — NewsAPI + GDELT news feed MCP wrapper.
Provides real-time news context for risk assessment and market intelligence.
All failures return DATA_UNAVAILABLE — never raises.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings
from asis.backend.mcp.base_mcp import BaseMCP

logger = get_logger(__name__)

_NEWSAPI_BASE = "https://newsapi.org/v2/everything"
_GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"


class NewsFeedMCP(BaseMCP):
    """
    Wraps NewsAPI and GDELT with retry, timeout, and sanitisation.

    Usage
    -----
    mcp = NewsFeedMCP()
    news   = await mcp.get_news("electric vehicles market", days_back=7)
    events = await mcp.get_gdelt_events("OPEC oil supply cut")
    """

    source_name = "newsapi_gdelt_feed"

    async def get_news(self, query: str, days_back: int = 7) -> str:
        """
        Fetch recent news articles from NewsAPI matching the query.

        Parameters
        ----------
        query : str
            Free-text search query.
        days_back : int
            How many days back to search (default 7).

        Returns
        -------
        str
            Formatted news articles string, or DATA_UNAVAILABLE on failure.
        """
        return await self._call_with_retry(self._do_get_news, query, days_back=days_back)

    async def get_gdelt_events(self, query: str) -> str:
        """
        Fetch geopolitical and macro events from the GDELT Doc 2.0 API.

        Parameters
        ----------
        query : str
            Free-text query for GDELT document search.

        Returns
        -------
        str
            Formatted GDELT events string, or DATA_UNAVAILABLE on failure.
        """
        return await self._call_with_retry(self._do_get_gdelt_events, query)

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _do_get_news(self, query: str, days_back: int = 7) -> str:
        api_key = self._settings.newsapi_key.get_secret_value()
        if not api_key:
            return "NEWS_FEED_UNAVAILABLE: NEWSAPI_KEY not configured."

        try:
            import httpx
        except ImportError:
            return "NEWS_FEED_UNAVAILABLE: httpx package not installed."

        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.get(
                _NEWSAPI_BASE,
                params={
                    "q": query,
                    "from": from_date,
                    "sortBy": "relevancy",
                    "pageSize": 10,
                    "language": "en",
                    "apiKey": api_key,
                },
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "ok":
            return f"NEWS_FEED_UNAVAILABLE: NewsAPI returned status={data.get('status')}"

        return _format_articles(data, source="NewsAPI", query=query)

    async def _do_get_gdelt_events(self, query: str) -> str:
        try:
            import httpx
        except ImportError:
            return "GDELT_UNAVAILABLE: httpx package not installed."

        # GDELT Doc 2.0 API — no auth required, rate limited
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.get(
                _GDELT_BASE,
                params={
                    "query": query,
                    "mode": "artlist",
                    "maxrecords": 10,
                    "format": "json",
                    "timespan": "7d",
                    "sort": "relevance",
                },
            )
            response.raise_for_status()
            data = response.json()

        return _format_gdelt_articles(data, query=query)


# ── Formatters ─────────────────────────────────────────────────────────────────

def _format_articles(data: dict[str, Any], source: str = "News", query: str = "") -> str:
    """Convert a raw NewsAPI response into clean text for LLM context."""
    articles = data.get("articles", [])
    if not articles:
        return f"No news articles found for query: {query!r}"

    lines: list[str] = [f"{source} — Results for: {query!r}\n"]
    for i, article in enumerate(articles, start=1):
        published = (article.get("publishedAt") or "")[:10]
        source_name = (article.get("source") or {}).get("name", "Unknown")
        title = article.get("title") or "Untitled"
        description = (article.get("description") or "")[:300]
        url = article.get("url") or ""
        lines.append(
            f"[{i}] {title} ({published})\n"
            f"    Source: {source_name}\n"
            f"    {description}\n"
            f"    URL: {url}\n"
        )
    return "\n".join(lines)


def _format_gdelt_articles(data: dict[str, Any], query: str = "") -> str:
    """Convert a GDELT Doc API response into clean text for LLM context."""
    articles = data.get("articles", [])
    if not articles:
        return f"No GDELT events found for query: {query!r}"

    lines: list[str] = [f"GDELT Global Events — Results for: {query!r}\n"]
    for i, article in enumerate(articles[:10], start=1):
        title = article.get("title") or "Untitled"
        url = article.get("url") or ""
        seendate = (article.get("seendate") or "")[:8]  # YYYYMMDD
        domain = article.get("domain") or ""
        language = article.get("language") or "en"
        tone = article.get("tone")
        tone_str = f" | Tone: {tone:.2f}" if isinstance(tone, (int, float)) else ""
        lines.append(
            f"[{i}] {title}\n"
            f"    Source: {domain} ({language.upper()}) | Date: {seendate}{tone_str}\n"
            f"    URL: {url}\n"
        )
    return "\n".join(lines)
