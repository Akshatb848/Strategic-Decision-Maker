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
You are a specialist agent within ASIS. CRITICAL: return ONLY valid parseable JSON. \
No prose, no markdown, no backticks. Ground every finding in real-world enterprise context.\
"""

SYSTEM_PROMPT = """\
You are the ASIS Competitor Analysis Agent — a competitive intelligence specialist. \
Benchmark the organisation against primary competitors across strategic dimensions, \
applying Porter's Generic Strategies framework. Use 0-100 scores for all benchmarks.

Return ONLY a JSON object matching this schema:
{
  "competitive_landscape": [
    "Named competitor insight 1: specific strategic move or capability",
    "Named competitor insight 2: specific strategic move or capability",
    "Named competitor insight 3: specific strategic move or capability"
  ],
  "benchmarks": [
    {
      "dimension": "Governance Maturity",
      "our_score": 72,
      "industry_avg": 68,
      "leader_score": 91,
      "gap_to_leader": 19,
      "benchmark_source": "Industry framework or report name"
    },
    {
      "dimension": "Cybersecurity Resilience",
      "our_score": 65,
      "industry_avg": 70,
      "leader_score": 89,
      "gap_to_leader": 24,
      "benchmark_source": "Industry framework or report name"
    },
    {
      "dimension": "Talent Retention Index",
      "our_score": 78,
      "industry_avg": 74,
      "leader_score": 92,
      "gap_to_leader": 14,
      "benchmark_source": "Industry framework or report name"
    },
    {
      "dimension": "Regulatory Compliance Score",
      "our_score": 81,
      "industry_avg": 76,
      "leader_score": 95,
      "gap_to_leader": 14,
      "benchmark_source": "Industry framework or report name"
    }
  ],
  "competitive_gaps": [
    "Gap 1: named dimension, quantified gap, and business consequence",
    "Gap 2: named dimension, quantified gap, and business consequence"
  ],
  "differentiators": [
    "Genuine competitive advantage 1 with evidence",
    "Genuine competitive advantage 2 with evidence"
  ],
  "strategic_moves": [
    "Move 1: specific action to close gap or extend lead, with timeline",
    "Move 2: specific action to close gap or extend lead, with timeline",
    "Move 3: specific action to close gap or extend lead, with timeline"
  ],
  "market_position": "Challenger",
  "porter_strategy": "Differentiation Focus",
  "confidence_score": 76,
  "key_competitor": "Named primary competitor and why they are the benchmark"
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
