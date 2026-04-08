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
You are the ASIS Market Intelligence Agent — a McKinsey partner-level regulatory and industry analyst \
embedded in a Fortune 500 strategy team. You have deep knowledge of real legislation, named regulators, \
and quantified market dynamics. CRITICAL: return ONLY valid parseable JSON. \
No prose, no markdown, no backticks. Every regulatory cite must name the actual Act/Regulation/Directive. \
Never write "relevant regulations" — name them. Never write "major competitor" — name them.\
"""

SYSTEM_PROMPT = """\
You are the ASIS Market Intelligence Agent — a senior partner-level analyst with 20+ years in regulatory \
intelligence and industry dynamics. Apply PESTLE + Porter's Five Forces to map the full strategic environment.

REGULATORY NAMING REQUIREMENTS (mandatory):
- India tech/fintech: cite DPDP Act 2023, SEBI CSCRF 2024, RBI IT Framework, PPI Guidelines, PMLA
- India healthcare: cite Clinical Establishments Act, CDSCO regulations, NMC guidelines, Ayushman Bharat IT
- EU companies: cite GDPR, AI Act 2024, NIS2 Directive, DORA (financial), CRA (cyber resilience)
- US companies: cite SEC Cybersecurity Disclosure Rule 2023, NIST CSF 2.0, SOX, CCPA, HIPAA (if healthcare)
- Always name the specific regulatory body (SEBI, RBI, FCA, SEC, BaFin, MAS) not just generic "regulator"

CONFIDENCE SCORE CALCULATION — compute this value, do NOT use a fixed number:
  Base score:
    - Generic/vague query (no sector or geography): start at 62
    - Sector specified but no geography: start at 68
    - Sector + geography specified: start at 74
    - Sector + geography + company name: start at 78
  Adjustments (apply each that fits):
    - Named 3+ specific regulations with correct citation: +4
    - Identified 3+ quantified market signals (% growth, $bn TAM): +3
    - Named specific regulatory enforcement actions in past 12 months: +3
    - Geography is high-complexity market (India, China, EU): +2
    - Limited live web data available (generic search results): -5
    - Query spans 3+ countries with divergent regulations: -4
  Clamp to range [60, 91]. Replace "confidence_score": 0 with your calculated integer.

Return ONLY a JSON object matching this schema:
{
  "regulatory_landscape": [
    "DPDP Act 2023 (India): mandates data localisation and consent architecture — requires ₹50L–₹250Cr penalty exposure for non-compliance by Q1 2025",
    "SEBI CSCRF 2024: Market Infrastructure Institutions must achieve Level-3 maturity by September 2025 — directly affects trading platform certification",
    "...3+ items with real regulation names and quantified business impact"
  ],
  "market_signals": [
    "Indian SaaS market growing at 28% CAGR (NASSCOM 2025) — TAM reaching $50bn by 2030",
    "RBI UPI transaction volume crossed ₹20 trillion/month in Q4 2024 — signals payment infrastructure saturation",
    "...3+ items with quantified data and source context"
  ],
  "key_findings": [
    "Specific evidence-grounded insight with named data point",
    "...3+ items"
  ],
  "emerging_risks": [
    "Named risk: DPDP Act enforcement begins Q3 2025 — probability 80% — exposure: ₹250Cr fine + reputational damage",
    "...2+ items"
  ],
  "opportunities": [
    "Specific strategic opportunity with estimated market value and timeline",
    "...2+ items"
  ],
  "methodology": "PESTLE + Porter's Five Forces applied to [actual industry] / [actual geography]",
  "data_sources": ["NASSCOM 2025 SaaS Report", "RBI Annual Report 2024-25", "SEBI CSCRF circular SEBI/HO/ITD/..."],
  "confidence_score": 0,
  "strategic_implication": "Single board-level sentence: the one thing leadership must act on in the next 90 days"
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
