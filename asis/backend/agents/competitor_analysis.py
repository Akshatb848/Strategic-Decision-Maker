"""
ASIS v3.0 — Competitor Analysis Agent.
Dissertation: Porter's Generic Strategies + Competitive Intelligence Matrix.
Multi-dimensional benchmarking with quantified gap analysis.
"""
from __future__ import annotations

import json

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.memory.qdrant_store import get_qdrant_store
from asis.backend.mcp.web_search import WebSearchMCP
from asis.backend.schemas.agent_outputs import CompetitorReport
from .base_agent import BaseAgent

logger = get_logger(__name__)

MASTER_PROMPT = """\
You are the ASIS Competitor Analysis Agent — a McKinsey-level competitive intelligence specialist \
with deep knowledge of real companies, M&A activity, and market positioning data. \
CRITICAL: return ONLY valid parseable JSON. No prose, no markdown, no backticks. \
NEVER use placeholder names like "Competitor A", "Company X", or "Leading Provider". \
Always name actual organisations (e.g. "Infosys", "TCS", "Wipro", "Accenture", "Salesforce"). \
If the exact company name is uncertain, name the most likely real competitor in that sector.\
"""

SYSTEM_PROMPT = """\
You are the ASIS Competitor Analysis Agent — a competitive intelligence partner with 20+ years \
mapping strategic landscapes for Global 500 clients. Apply Porter's Generic Strategies + Competitive \
Intelligence Matrix to deliver board-ready benchmarking.

COMPETITOR NAMING REQUIREMENTS (mandatory — failure to comply invalidates output):
  - India IT services: TCS, Infosys, Wipro, HCL Tech, Tech Mahindra, Mphasis, Persistent Systems
  - India fintech: Razorpay, PayU, BillDesk, PhonePe, Paytm, CRED, Slice, Jupiter
  - India SaaS: Zoho, Freshworks, Chargebee, CleverTap, Postman, BrowserStack
  - Global cloud: AWS, Azure (Microsoft), GCP (Google), Oracle Cloud, IBM Cloud
  - Global consulting: McKinsey, BCG, Bain, Deloitte, PwC, Accenture Strategy
  - If company is a startup: name the nearest funded competitor (Crunchbase Series B+)
  - NEVER use "Competitor A/B/C" or "Major Provider" — this will cause output rejection

BENCHMARK SCORING REQUIREMENTS:
  - Scores must reflect actual capability gaps — not illustrative round numbers
  - gap_to_leader = leader_score - our_score (must be arithmetically correct)
  - benchmark_source must cite an actual framework, analyst report, or public disclosure
    (e.g. "Gartner Magic Quadrant 2025", "NASSCOM DSCI Survey 2024", "SEC 10-K filing")
  - Use 4–6 dimensions specific to the company's sector

CONFIDENCE SCORE CALCULATION — compute this value, do NOT use a fixed number:
  Base score:
    - Generic query with no company or sector: 58
    - Sector known: 65
    - Sector + company name: 71
    - Sector + company name + geography + named competitors found: 78
  Adjustments:
    - Named 3+ actual competitors with evidence of recent strategic moves: +5
    - Quantified benchmark gaps (not estimated): +4
    - Referenced real M&A or product launch in past 18 months: +3
    - Benchmarks based on well-known public framework (Gartner/Forrester/IDC): +3
    - Query is early-stage startup in niche market (hard to find competitors): -6
    - No web intelligence available — working from priors only: -5
  Clamp to range [58, 90]. Replace "confidence_score": 0 with your calculated integer.

Return ONLY a JSON object matching this schema:
{
  "competitive_landscape": [
    "Infosys: acquired Danske Bank IT subsidiary in Jan 2025 — signals aggressive BFSI expansion in EU markets",
    "TCS: launched TCS Cognitive Business Operations platform Q3 2024 — directly competes with ServiceNow in ITSM",
    "Named competitor insight 3: specific announced strategic move, product, or acquisition with date"
  ],
  "benchmarks": [
    {
      "dimension": "AI/ML Platform Maturity",
      "our_score": 62,
      "industry_avg": 71,
      "leader_score": 89,
      "gap_to_leader": 27,
      "benchmark_source": "Gartner Magic Quadrant for AI Services 2025"
    },
    {
      "dimension": "Regulatory Compliance Automation",
      "our_score": 74,
      "industry_avg": 69,
      "leader_score": 93,
      "gap_to_leader": 19,
      "benchmark_source": "NASSCOM DSCI Cybersecurity Survey 2024"
    },
    {
      "dimension": "Sector-relevant dimension 3",
      "our_score": 0,
      "industry_avg": 0,
      "leader_score": 0,
      "gap_to_leader": 0,
      "benchmark_source": "Actual report name"
    }
  ],
  "competitive_gaps": [
    "Dimension name: gap of X points vs leader [Company Name] — business consequence: specific risk of contract loss or margin erosion",
    "Dimension name: gap of Y points — consequence: specific market share risk over 18 months"
  ],
  "differentiators": [
    "Specific genuine competitive advantage with evidence (e.g. proprietary dataset, certification, patent)",
    "Specific advantage 2 with evidence"
  ],
  "strategic_moves": [
    "Move 1: close AI/ML gap — partner with [specific vendor] or acquire [named startup] — 12-month timeline",
    "Move 2: extend regulatory compliance lead — certify to ISO 42001 (AI Management) by Q4 2025",
    "Move 3: specific action to address named gap, with accountable owner and milestone"
  ],
  "market_position": "Challenger",
  "porter_strategy": "Differentiation Focus",
  "confidence_score": 0,
  "key_competitor": "Named primary competitor (e.g. TCS) — and specifically why they are the benchmark to close the gap against"
}\
"""


class CompetitorAnalysisAgent(BaseAgent):
    name = "competitor_analysis"
    description = "Porter's Generic Strategies benchmarking, competitive gap analysis, strategic moves."

    def __init__(self) -> None:
        super().__init__()
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

        # Watchlist cache
        watchlist = state.get("metadata", {}).get("competitor_watchlist", {})
        watchlist_section = ""
        if watchlist:
            watchlist_section = "## Competitor Watchlist (WF07):\n" + json.dumps(watchlist, indent=2)[:2000] + "\n\n"
            await self._log(state, "info", f"[COMPETITOR ANALYSIS] WF07 watchlist loaded — {len(watchlist) if isinstance(watchlist, list) else 'dict'} entries")
        else:
            await self._log(state, "info", f"[COMPETITOR ANALYSIS] Loading competitor intelligence for {sector} / {location}...")

        await self._log(state, "info", "[COMPETITOR ANALYSIS] Scanning Qdrant RAG for internal competitor intelligence...")
        qdrant = get_qdrant_store()
        rag_docs = await qdrant.retrieve(
            query=f"{sector} {location} competitor analysis market leaders benchmarks",
            tenant_id=tenant_id, doc_type="competitor_intel", top_k=4,
        )
        rag_section = ""
        if rag_docs:
            rag_section = "## Internal Competitor Intelligence (Qdrant RAG):\n" + "\n".join(f"[{i+1}] {d.text[:350]}" for i, d in enumerate(rag_docs)) + "\n\n"
            await self._log(state, "info", f"[COMPETITOR ANALYSIS] RAG hit — {len(rag_docs)} documents")

        await self._log(state, "info", f"[COMPETITOR ANALYSIS] Querying Tavily — live competitor profiles and strategic moves ({location})...")
        web_results = await self._web_search.search(f"top competitors {sector} {location} market position strategy 2025", max_results=5)
        moves_results = await self._web_search.search(f"{sector} {location} acquisition partnership M&A 2025", max_results=3)

        objective = task_plan.get("agent_assignments", {}).get(self.name, (
            "Apply Porter's Generic Strategies, benchmark across 4+ dimensions, identify competitive gaps and strategic moves."
        ))
        await self._log(state, "info", "[COMPETITOR ANALYSIS] Calling LLM — Porter's Generic Strategies + multi-dimensional benchmarking + gap analysis...")

        user_message = (
            f"Orchestrator assignment: {objective}\nProblem: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"{watchlist_section}{rag_section}"
            f"## Competitor Profiles (Tavily):\n{web_results}\n\n"
            f"## Strategic Moves (Tavily):\n{moves_results}\n\n"
            f"Benchmark {company_name} in {sector} / {location}. Return CompetitorReport JSON now."
        )

        report, tokens = await self._call_llm_json(f"{MASTER_PROMPT}\n\n{SYSTEM_PROMPT}", user_message, CompetitorReport)
        meta = self._accumulate_tokens(state, tokens)
        await self._log(state, "info", f"[COMPETITOR ANALYSIS] Complete — {len(report.benchmarks)} benchmark dimensions | Position: {report.market_position} | Key rival: {report.key_competitor}")
        logger.info("competitor_analysis_complete", company=company_name, benchmarks=len(report.benchmarks), tokens=tokens)
        return {**state, "competitor_brief": report.model_dump(), "metadata": meta}
