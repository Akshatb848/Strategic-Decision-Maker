"""
ASIS v3.0 — Market Intelligence Agent.
Environmental scanning: macro trends, market sizing, TAM/SAM/SOM, industry dynamics,
regulatory landscape, and entry barriers.

Data sources (in priority order):
  1. Qdrant RAG — internal market reports pre-loaded by tenant
  2. Tavily web search (WebSearchMCP) — live web intelligence
  3. NewsAPI (NewsFeedMCP) — recent industry news
"""
from __future__ import annotations

import json
from typing import Any

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.memory.qdrant_store import get_qdrant_store
from asis.backend.mcp.web_search import WebSearchMCP
from asis.backend.mcp.news_feed import NewsFeedMCP
from asis.backend.schemas.agent_outputs import MarketIntelligenceReport, DataSource
from .base_agent import BaseAgent

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a Senior Market Intelligence Analyst at a top-tier global management consulting firm
(McKinsey / BCG calibre). You are conducting a comprehensive market intelligence assessment for
a multinational corporation's strategic decision.

## Your mandate
Produce a rigorous, quantitative market intelligence report that will feed downstream financial
modelling and risk assessment agents. The quality of your output directly determines the quality
of the final board-level strategic brief.

## Mandatory requirements
1. **Quantitative precision**: Provide market size in USD billions, CAGR as a percentage,
   and a specific forecast year. If exact figures are unavailable, provide a credible range
   with stated methodology (e.g., top-down TAM, bottom-up SOM).
2. **Source every data point**: Cite the publication, database, or report name and year for
   each key claim. Do not fabricate figures — flag uncertainty explicitly.
3. **Regulatory rigor**: Flag ALL regulatory considerations with jurisdiction and impact level.
   Include data localisation laws, sector-specific licensing, foreign ownership caps, tariffs.
4. **Entry barriers**: Identify structural, regulatory, capital, and knowledge barriers to entry.
5. **Key trends**: Identify minimum 3 macro trends shaping the market over the next 5 years.
   Include technology shifts, demographic changes, geopolitical drivers, and ESG pressures.
6. **Analyst commentary**: Write 200+ words of substantive commentary on the strategic
   implications for the querying company. Do not be generic — reference the specific context.

## RAG context usage
The user message will include document excerpts retrieved from the company's internal knowledge
base (Qdrant RAG). Prioritise this internal intelligence over generic web search results.
Clearly note when you are drawing on internal documents.

## Output format
Return valid JSON ONLY — no preamble, no markdown fences, no explanation outside the JSON.
The JSON must exactly match the MarketIntelligenceReport schema:

{
  "market_name": "string — specific market name (e.g. 'B2B SaaS in Southeast Asia')",
  "market_size_usd_bn": number (positive float),
  "growth_rate_cagr_pct": number (float, can be negative),
  "forecast_year": integer (2024-2035),
  "key_trends": ["trend1 (min 3 items)"],
  "regulatory_flags": ["regulatory consideration 1"],
  "entry_barriers": ["barrier 1"],
  "rag_sources": [
    {"name": "string", "url": "string", "source_type": "rag", "relevance_score": 0.0-1.0}
  ],
  "web_sources": [
    {"name": "string", "url": "string", "source_type": "web", "relevance_score": 0.0-1.0}
  ],
  "analyst_commentary": "string (200+ words of substantive strategic commentary)"
}
"""


class MarketIntelligenceAgent(BaseAgent):
    """Agent 2 — Market Intelligence. Qdrant RAG + Tavily web + NewsAPI."""

    name = "market_intelligence"
    description = "Market sizing, trends, regulatory landscape, and entry barrier analysis."

    def __init__(self) -> None:
        super().__init__()
        self._web_search = WebSearchMCP()
        self._news_feed = NewsFeedMCP()

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        task_plan = state.get("task_plan", {})
        tenant_id = self._get_tenant_id(state)

        sector = context.get("sector", "")
        target_market = context.get("target_market", "")
        geography = context.get("geography", "")
        company_name = context.get("company_name") or context.get("name", "")

        # ── Step 1: Qdrant RAG retrieval (internal market reports) ────────────
        await self._log(state, "info", f"[MARKET INTELLIGENCE] Scanning internal knowledge base (Qdrant RAG) for {sector} market data...")
        qdrant = get_qdrant_store()
        rag_query = f"{target_market or sector} market size trends regulatory {geography}"
        rag_docs = await qdrant.retrieve(
            query=rag_query,
            tenant_id=tenant_id,
            doc_type="market_report",
            top_k=5,
        )

        rag_context = ""
        rag_hits = len(rag_docs)
        rag_sources_meta: list[dict[str, Any]] = []

        if rag_docs:
            rag_context = "## Internal Market Reports (from Qdrant RAG):\n"
            for i, doc in enumerate(rag_docs, start=1):
                rag_context += f"[RAG-{i}] (score={doc.score:.2f}) {doc.text[:600]}\n\n"
                rag_sources_meta.append({
                    "name": doc.metadata.get("source", f"Internal Document {i}"),
                    "url": doc.metadata.get("url", ""),
                    "source_type": "rag",
                    "relevance_score": round(min(1.0, doc.score), 4),
                })
            logger.info(
                "market_intelligence_rag",
                hits=rag_hits,
                tenant_id=tenant_id,
            )
        else:
            rag_context = "## Internal Market Reports: No documents retrieved from Qdrant.\n"
            logger.info("market_intelligence_rag_miss", tenant_id=tenant_id)

        # ── Step 2: Tavily web search (gap-fill for live market data) ─────────
        await self._log(state, "info", f"[MARKET INTELLIGENCE] Querying live web intelligence (Tavily) — {target_market or sector} market data...")
        web_query = (
            f"{target_market or sector} market size growth forecast {geography} "
            f"regulatory environment 2024 2025"
        )
        web_results = await self._web_search.search(web_query, max_results=5)

        # ── Step 3: NewsAPI for recent industry news ───────────────────────────
        await self._log(state, "info", "[MARKET INTELLIGENCE] Retrieving recent industry news (NewsAPI)...")
        news_query = f"{target_market or sector} {geography} industry trends 2024 2025"
        news_results = await self._news_feed.fetch(news_query, max_results=5)

        # ── Step 4: Build objective from TaskPlan ─────────────────────────────
        objective = _get_objective(task_plan, self.name)

        # ── Step 5: Assemble LLM prompt ───────────────────────────────────────
        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Agent Objective: {objective}\n\n"
            f"{rag_context}\n"
            f"## Web Search Results (Tavily):\n{web_results}\n\n"
            f"## Recent Industry News (NewsAPI):\n{news_results}\n\n"
            "Produce the MarketIntelligenceReport JSON now. "
            "Use internal RAG documents as primary sources where available. "
            "Supplement with web/news data for any gaps. "
            "Be specific about the market named in the query — do not produce a generic report."
        )

        # ── Step 6: LLM call ───────────────────────────────────────────────────
        await self._log(state, "info", f"[MARKET INTELLIGENCE] Calling LLM — synthesising PESTLE, market sizing, trend analysis ({rag_hits} RAG docs, web + news data)...")
        report, tokens = await self._call_llm_json(
            SYSTEM_PROMPT,
            user_message,
            MarketIntelligenceReport,
        )

        # ── Step 7: Update state ───────────────────────────────────────────────
        meta = self._accumulate_tokens(state, tokens)
        meta["rag_hits"] = rag_hits
        meta["rag_sources"] = rag_sources_meta

        await self._log(state, "info", f"[MARKET INTELLIGENCE] Market: {report.market_name} | Size: ${report.market_size_usd_bn}B | CAGR: {report.growth_rate_cagr_pct}% | {len(report.key_trends)} trends identified")
        logger.info("market_intelligence_complete", market=report.market_name, market_size_usd_bn=report.market_size_usd_bn, rag_hits=rag_hits, tokens=tokens)

        return {
            **state,
            "market_report": report.model_dump(),
            "metadata": meta,
        }


def _get_objective(task_plan: dict[str, Any], agent_name: str) -> str:
    for task in task_plan.get("subtasks", []):
        if task.get("agent") == agent_name:
            return task.get("objective", "")
    return "Conduct comprehensive market intelligence analysis covering market size, trends, regulatory landscape, and entry barriers."
