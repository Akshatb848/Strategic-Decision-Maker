"""
MCP Financial Data — Financial Modeling Prep (FMP) API wrapper.
Provides financial ratios, sector peers, and company data for financial reasoning.
"""

from __future__ import annotations

from ..config import get_logger, get_settings
from .base_mcp import BaseMCP

settings = get_settings()
logger = get_logger(__name__)

FMP_BASE = "https://financialmodelingprep.com/api/v3"


class FinancialDataMCP(BaseMCP):
    """Wraps FMP API for financial and sector data."""

    source_name = "fmp_financial_data"

    async def get_sector_peers(self, sector: str, *, limit: int = 5) -> str:
        """
        Return financial metrics for publicly listed peers in the sector.
        Falls back to DATA_UNAVAILABLE on any error.
        """
        return await self._call_with_retry(self._do_sector_peers, sector, limit=limit)

    async def get_company_profile(self, ticker: str) -> str:
        """Fetch profile + key ratios for a specific ticker."""
        return await self._call_with_retry(self._do_company_profile, ticker)

    # ── Internal ──────────────────────────────────────────────────────────

    async def _do_sector_peers(self, sector: str, *, limit: int = 5) -> str:
        api_key = settings.fmp_api_key.get_secret_value()
        if not api_key:
            return "FINANCIAL_DATA_UNAVAILABLE: FMP_API_KEY not configured."

        try:
            import httpx
        except ImportError:
            return "FINANCIAL_DATA_UNAVAILABLE: httpx not installed."

        # Map generic sector names to FMP sector strings
        sector_map = {
            "technology": "Technology",
            "tech": "Technology",
            "financial": "Financial Services",
            "finance": "Financial Services",
            "healthcare": "Healthcare",
            "consumer": "Consumer Cyclical",
            "energy": "Energy",
            "industrial": "Industrials",
            "utilities": "Utilities",
            "real estate": "Real Estate",
            "materials": "Basic Materials",
            "communication": "Communication Services",
        }
        fmp_sector = sector_map.get(sector.lower(), sector)

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(
                f"{FMP_BASE}/stock-screener",
                params={
                    "sector": fmp_sector,
                    "limit": limit,
                    "isEtf": "false",
                    "apikey": api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return _format_peers(data[:limit])

    async def _do_company_profile(self, ticker: str) -> str:
        api_key = settings.fmp_api_key.get_secret_value()
        if not api_key:
            return "FINANCIAL_DATA_UNAVAILABLE: FMP_API_KEY not configured."

        try:
            import httpx
        except ImportError:
            return "FINANCIAL_DATA_UNAVAILABLE: httpx not installed."

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(
                f"{FMP_BASE}/profile/{ticker.upper()}",
                params={"apikey": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        if not data:
            return f"No profile data found for {ticker}"

        p = data[0]
        return (
            f"Company: {p.get('companyName', ticker)}\n"
            f"Sector: {p.get('sector', 'N/A')} | Industry: {p.get('industry', 'N/A')}\n"
            f"Revenue: ${p.get('revenue', 0) / 1e6:.1f}M | "
            f"Market Cap: ${p.get('mktCap', 0) / 1e9:.2f}B\n"
            f"PE Ratio: {p.get('pe', 'N/A')} | "
            f"EV/EBITDA: {p.get('enterpriseValueOverEBITDA', 'N/A')}\n"
            f"Description: {str(p.get('description', ''))[:300]}\n"
        )


def _format_peers(peers: list) -> str:
    if not peers:
        return "No peer data available."
    lines = ["Sector Peer Companies:"]
    for p in peers:
        mktcap = p.get("marketCap", 0)
        lines.append(
            f"  • {p.get('companyName', p.get('symbol', 'Unknown'))} ({p.get('symbol', '')})\n"
            f"    Market Cap: ${mktcap / 1e9:.2f}B | "
            f"Price: ${p.get('price', 'N/A')} | "
            f"Sector: {p.get('sector', 'N/A')}"
        )
    return "\n".join(lines)
