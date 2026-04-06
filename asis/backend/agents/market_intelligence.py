"""
ASIS v3.0 — Market Intelligence Agent.
Dissertation: PESTLE + Porter's Five Forces environmental scanning.
"""
from __future__ import annotations

import json
from typing import Any

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.memory.qdrant_store import get_qdrant_store
from asis.backend.mcp.news_feed import NewsFeedMCP
from asis.backend.mcp.web_search import WebSearchMCP
from asis.backend.schemas.agent_outputs import MarketIntelReport
from .base_agent import BaseAgent

logger = get_logger(__name__)

MASTER_PROMPT = """\
You are a specialist agent within ASIS (Autonomous Strategic Intelligence System), a multi-agent AI \
platform for enterprise strategic decision-making. CRITICAL: return ONLY valid parseable JSON. \
No prose, no markdown, no backticks. Ground every finding in real-world enterprise context.\
"""

SYSTEM_PROMPT = """\
You are the ASIS Market Intelligence Agent — a senior analyst specialising in regulatory intelligence \
and industry dynamics. Apply PESTLE analysis and identify signals affecting the organisation's strategic position.

Return ONLY a JSON object matching this schema:
{
  "regulatory_landscape": ["Specific regulation and direct operational impact", "...3+ items"],
  "market_signals": ["Quantified market trend with source context", "...3+ items"],
  "key_findings": ["Specific evidence-grounded insight 1", "...3+ items"],
  "emerging_risks": ["Named risk with probability and business impact", "...2+ items"],
  "opportunities": ["Specific strategic opportunity with estimated value", "...2+ items"],
  "methodology": "PESTLE + Porter's Five Forces applied to [industry/region]",
  "data_sources": ["Source 1", "Source 2", "Source 3"],
  "confidence_score": 82,
  "strategic_implication": "Single board-level sentence: what leadership must act on immediately"
}\
"""


class MarketIntelligenceAgent(BaseAgent):
    name = "market_intelligence"
    description = "PESTLE environmental scan, regulatory landscape, market signal identification."

    def __init__(self) -> None:
        super().__init__()
        self._news_feed = NewsFeedMCP()
        self._web_search = WebSearchMCP()

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        task_plan = state.get("task_plan", {})
        tenant_id = self._get_tenant_id(state)

        sector = context.get("sector", "")
        target_market = context.get("target_market", "")
        geography = context.get("geography", "")
        company_name = context.get("company_name") or context.get("name", "")
        location = target_market or geography

        await self._log(state, "info", f"[MARKET INTELLIGENCE] Scanning Qdrant RAG — {sector} / {location}...")
        qdrant = get_qdrant_store()
        rag_docs = await qdrant.retrieve(
            query=f"{sector} {location} market trends regulatory landscape",
            tenant_id=tenant_id, doc_type="market_report", top_k=3,
        )
        rag_context = ""
        if rag_docs:
            rag_context = "## Internal Knowledge Base:\n" + "\n".join(f"[{i+1}] {d.text[:350]}" for i, d in enumerate(rag_docs)) + "\n\n"
            await self._log(state, "info", f"[MARKET INTELLIGENCE] RAG hit — {len(rag_docs)} documents")

        await self._log(state, "info", "[MARKET INTELLIGENCE] Querying Tavily for live regulatory and market intelligence...")
        web_results = await self._web_search.search(f"{location} {sector} regulatory landscape market trends 2025 2026", max_results=5)

        await self._log(state, "info", "[MARKET INTELLIGENCE] Fetching recent industry news (NewsAPI)...")
        news_results = await self._news_feed.fetch(f"{sector} {location} market growth regulation 2025", max_results=4)

        objective = task_plan.get("agent_assignments", {}).get(self.name, "Apply PESTLE to map regulatory landscape, market signals, and strategic opportunities.")
        await self._log(state, "info", "[MARKET INTELLIGENCE] Calling LLM — PESTLE analysis, regulatory mapping, signal identification...")

        user_message = (
            f"Orchestrator assignment: {objective}\nProblem: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"{rag_context}"
            f"## Web Intelligence (Tavily):\n{web_results}\n\n"
            f"## Recent News:\n{news_results}\n\n"
            f"Analyse {company_name} in {sector} / {location}. Return MarketIntelReport JSON now."
        )

        report, tokens = await self._call_llm_json(f"{MASTER_PROMPT}\n\n{SYSTEM_PROMPT}", user_message, MarketIntelReport)
        meta = self._accumulate_tokens(state, tokens)
        await self._log(state, "info", f"[MARKET INTELLIGENCE] Complete — {len(report.regulatory_landscape)} regulatory signals | Implication: {report.strategic_implication[:80]}...")
        logger.info("market_intelligence_complete", company=company_name, tokens=tokens)
        return {**state, "market_report": report.model_dump(), "metadata": meta}
