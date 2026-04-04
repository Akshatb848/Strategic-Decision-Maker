"""
ASIS v3.0 — Financial Modeling Prep (FMP) financial data MCP wrapper.
Provides company profiles, peer metrics, and sector overviews for the
financial reasoning agent.  All failures return DATA_UNAVAILABLE — never raises.
"""
from __future__ import annotations

from typing import Any

from asis.backend.config.logging import get_logger
from asis.backend.config.settings import get_settings
from asis.backend.mcp.base_mcp import BaseMCP

logger = get_logger(__name__)

FMP_BASE = "https://financialmodelingprep.com/api/v3"

# Map generic sector names to FMP sector strings
_SECTOR_MAP: dict[str, str] = {
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


class FinancialDataMCP(BaseMCP):
    """
    Wraps the FMP API for company profiles, peer metrics, and sector overviews.

    Usage
    -----
    mcp = FinancialDataMCP()
    profile = await mcp.get_company_profile("AAPL")
    peers   = await mcp.get_peer_metrics("AAPL")
    sector  = await mcp.get_sector_overview("technology")
    """

    source_name = "fmp_financial_data"

    async def get_company_profile(self, ticker: str) -> str:
        """
        Fetch profile and key financial ratios for a specific ticker.

        Parameters
        ----------
        ticker : str
            Stock ticker symbol (e.g. "AAPL", "MSFT").

        Returns
        -------
        str
            Formatted company profile string, or DATA_UNAVAILABLE on failure.
        """
        return await self._call_with_retry(self._do_company_profile, ticker)

    async def get_peer_metrics(self, ticker: str) -> str:
        """
        Fetch financial metrics for peers in the same sector as the given ticker.

        Parameters
        ----------
        ticker : str
            Stock ticker symbol used to look up the sector, then peers.

        Returns
        -------
        str
            Formatted peer metrics string, or DATA_UNAVAILABLE on failure.
        """
        return await self._call_with_retry(self._do_peer_metrics, ticker)

    async def get_sector_overview(self, sector: str) -> str:
        """
        Fetch publicly listed companies and their key metrics for a given sector.

        Parameters
        ----------
        sector : str
            Sector name (e.g. "technology", "healthcare").  Case-insensitive.

        Returns
        -------
        str
            Formatted sector overview string, or DATA_UNAVAILABLE on failure.
        """
        return await self._call_with_retry(self._do_sector_overview, sector)

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _do_company_profile(self, ticker: str) -> str:
        api_key = self._get_api_key()
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
            return f"No profile data found for ticker: {ticker.upper()}"

        p = data[0]
        return (
            f"Company: {p.get('companyName', ticker)}\n"
            f"Ticker: {p.get('symbol', ticker.upper())}\n"
            f"Sector: {p.get('sector', 'N/A')} | Industry: {p.get('industry', 'N/A')}\n"
            f"Exchange: {p.get('exchangeShortName', 'N/A')}\n"
            f"Revenue: ${p.get('revenue', 0) / 1e6:.1f}M | "
            f"Market Cap: ${p.get('mktCap', 0) / 1e9:.2f}B\n"
            f"PE Ratio: {p.get('pe', 'N/A')} | "
            f"EV/EBITDA: {p.get('enterpriseValueOverEBITDA', 'N/A')}\n"
            f"Beta: {p.get('beta', 'N/A')} | "
            f"Dividend Yield: {p.get('lastDiv', 'N/A')}\n"
            f"52W High: {p.get('range', 'N/A')}\n"
            f"CEO: {p.get('ceo', 'N/A')} | "
            f"Employees: {p.get('fullTimeEmployees', 'N/A')}\n"
            f"Description: {str(p.get('description', ''))[:400]}\n"
        )

    async def _do_peer_metrics(self, ticker: str) -> str:
        api_key = self._get_api_key()
        if not api_key:
            return "FINANCIAL_DATA_UNAVAILABLE: FMP_API_KEY not configured."

        try:
            import httpx
        except ImportError:
            return "FINANCIAL_DATA_UNAVAILABLE: httpx not installed."

        # Step 1: Get the ticker's sector from its profile
        sector = "Technology"  # default
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(
                    f"{FMP_BASE}/profile/{ticker.upper()}",
                    params={"apikey": api_key},
                )
                resp.raise_for_status()
                profile_data = resp.json()
                if profile_data:
                    sector = profile_data[0].get("sector", "Technology")
        except Exception:
            pass  # fall through with default sector

        # Step 2: Fetch peer companies in the same sector via stock screener
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(
                f"{FMP_BASE}/stock-screener",
                params={
                    "sector": sector,
                    "limit": 6,
                    "isEtf": "false",
                    "apikey": api_key,
                },
            )
            resp.raise_for_status()
            peers = resp.json()

        # Exclude the queried ticker itself if present
        peers = [p for p in peers if p.get("symbol", "").upper() != ticker.upper()][:5]
        return _format_peers(peers, context=f"Sector peers for {ticker.upper()} ({sector})")

    async def _do_sector_overview(self, sector: str) -> str:
        api_key = self._get_api_key()
        if not api_key:
            return "FINANCIAL_DATA_UNAVAILABLE: FMP_API_KEY not configured."

        try:
            import httpx
        except ImportError:
            return "FINANCIAL_DATA_UNAVAILABLE: httpx not installed."

        fmp_sector = _SECTOR_MAP.get(sector.lower(), sector)

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(
                f"{FMP_BASE}/stock-screener",
                params={
                    "sector": fmp_sector,
                    "limit": 10,
                    "isEtf": "false",
                    "apikey": api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return _format_sector_overview(data[:10], sector=fmp_sector)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _get_api_key(self) -> str:
        return self._settings.fmp_api_key.get_secret_value()


# ── Formatters ─────────────────────────────────────────────────────────────────

def _format_peers(peers: list[dict[str, Any]], context: str = "Sector Peers") -> str:
    if not peers:
        return "No peer data available."
    lines = [f"{context}:"]
    for p in peers:
        mktcap = p.get("marketCap") or 0
        lines.append(
            f"  • {p.get('companyName', p.get('symbol', 'Unknown'))} ({p.get('symbol', '')})\n"
            f"    Market Cap: ${mktcap / 1e9:.2f}B | "
            f"Price: ${p.get('price', 'N/A')} | "
            f"Sector: {p.get('sector', 'N/A')} | "
            f"Industry: {p.get('industry', 'N/A')}"
        )
    return "\n".join(lines)


def _format_sector_overview(companies: list[dict[str, Any]], sector: str) -> str:
    if not companies:
        return f"No data available for sector: {sector}"
    lines = [f"Sector Overview — {sector} ({len(companies)} companies):"]
    total_cap = sum((c.get("marketCap") or 0) for c in companies)
    lines.append(f"  Total Market Cap (sample): ${total_cap / 1e9:.1f}B\n")
    for c in companies:
        mktcap = c.get("marketCap") or 0
        lines.append(
            f"  • {c.get('companyName', c.get('symbol', 'Unknown'))} ({c.get('symbol', '')})\n"
            f"    Market Cap: ${mktcap / 1e9:.2f}B | "
            f"Price: ${c.get('price', 'N/A')} | "
            f"Industry: {c.get('industry', 'N/A')}"
        )
    return "\n".join(lines)
