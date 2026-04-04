"""
ASIS v3.0 — Competitor Analysis Agent.
Porter's Five Forces analysis + direct competitor profiling + strategic white space mapping.

Data sources (in priority order):
  1. n8n WF07 competitor watchlist cache — pre-loaded into state metadata
  2. Qdrant RAG — internal competitor intelligence documents
  3. Tavily web search (WebSearchMCP) — live competitor profiles
"""
from __future__ import annotations

import json
from typing import Any

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.memory.qdrant_store import get_qdrant_store
from asis.backend.mcp.web_search import WebSearchMCP
from asis.backend.schemas.agent_outputs import CompetitorBrief
from .base_agent import BaseAgent

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a Competitive Strategy Specialist at a top-tier strategy consultancy (Bain / McKinsey calibre).
You are conducting a rigorous competitive analysis for a multinational corporation considering a major
strategic move. Your output feeds directly into the board-level strategic brief.

## Your mandate
Deliver a comprehensive competitive intelligence brief that enables the querying company to
understand its competitive environment, identify threats and opportunities, and define a winning
position in the target market.

## Mandatory requirements
1. **Porter's Five Forces — exactly 5**: Analyse ALL five forces with numeric intensity scores (1-10)
   and substantive rationale. The five force names MUST exactly match the schema literals:
   - supplier_power
   - buyer_power
   - competitive_rivalry
   - threat_of_substitution
   - threat_of_new_entry
   Missing or misnamed forces will fail validation.

2. **Competitor profiles (2-8)**: For each top competitor provide:
   - Full name, HQ country, estimated revenue, and market share
   - At least 1 strength and 1 weakness (specific, not generic)
   - Recent strategic moves (acquisitions, partnerships, product launches, geographic expansion)
   - Threat level to the querying company: low/medium/high/critical
   - Mark watchlist_sourced=true if the competitor appears in the n8n WF07 watchlist cache

3. **Strategic white space**: Identify at least 1 uncontested opportunity area that the querying
   company could exploit given competitor gaps and market dynamics.

4. **Competitive moat assessment**: Write 100+ words assessing the querying company's potential
   to build a sustainable competitive advantage in this market.

5. **Sources**: List all sources (watchlist, RAG documents, web searches) used.

6. **No fabrication**: Use available data. If specific competitor data is unavailable, note this
   and use publicly known market structure information.

## Watchlist integration
If n8n WF07 competitor watchlist data is provided, this is the highest-priority source.
Use watchlist entries as the basis for competitor profiles and supplement with web data.

## Internal intelligence
Qdrant RAG documents may contain internal competitor intelligence from the company's knowledge base.
Treat this as confidential internal source and prioritise it for insight differentiation.

## Output format
Return valid JSON ONLY — no preamble, no markdown fences.
The JSON must exactly match the CompetitorBrief schema:

{
  "company_name": "string (company being analysed)",
  "industry": "string (industry / sector)",
  "five_forces": [
    {
      "force": "supplier_power|buyer_power|competitive_rivalry|threat_of_substitution|threat_of_new_entry",
      "score": integer 1-10,
      "rationale": "string (min 30 chars)",
      "key_factors": ["factor1", "factor2"]
    }
  ],
  "top_competitors": [
    {
      "name": "string",
      "hq_country": "string",
      "revenue_usd_bn": number,
      "market_share_pct": number 0-100,
      "strengths": ["strength1"],
      "weaknesses": ["weakness1"],
      "strategic_moves": ["recent move1"],
      "threat_level": "low|medium|high|critical",
      "watchlist_sourced": true|false
    }
  ],
  "strategic_white_space": ["opportunity area 1"],
  "competitive_moat_assessment": "string (min 80 chars)",
  "sources": ["source1", "source2"]
}
"""


class CompetitorAnalysisAgent(BaseAgent):
    """Agent 5 — Competitor Analysis. WF07 watchlist + Qdrant RAG + Tavily web."""

    name = "competitor_analysis"
    description = "Porter Five Forces, competitor profiling, and strategic white space analysis."

    def __init__(self) -> None:
        super().__init__()
        self._web_search = WebSearchMCP()

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        task_plan = state.get("task_plan", {})
        metadata = state.get("metadata", {})
        tenant_id = self._get_tenant_id(state)

        sector = context.get("sector", "")
        target_market = context.get("target_market", "")
        geography = context.get("geography", "")
        company_name = context.get("company_name") or context.get("name", "")

        # ── Step 1: n8n WF07 competitor watchlist cache ───────────────────────
        watchlist_data = metadata.get("competitor_watchlist", {})
        watchlist_available = bool(watchlist_data)
        watchlist_section = ""

        if watchlist_available:
            watchlist_section = (
                "## Competitor Watchlist (from n8n WF07 cache — highest priority source):\n"
                + json.dumps(watchlist_data, indent=2)[:3000]
                + "\n"
            )
            logger.info(
                "competitor_analysis_watchlist_hit",
                company=company_name,
                entries=len(watchlist_data) if isinstance(watchlist_data, list) else "dict",
            )
        else:
            watchlist_section = (
                "## Competitor Watchlist: Not available — using web search and RAG as primary sources.\n"
            )
            logger.info(
                "competitor_analysis_watchlist_miss",
                company=company_name,
            )

        # ── Step 2: Qdrant RAG for internal competitor intelligence ────────────
        qdrant = get_qdrant_store()
        rag_query = (
            f"{sector} {target_market or geography} competitor analysis market leaders"
        )
        rag_docs = await qdrant.retrieve(
            query=rag_query,
            tenant_id=tenant_id,
            doc_type="competitor_intel",
            top_k=5,
        )

        rag_context = ""
        if rag_docs:
            rag_context = "## Internal Competitor Intelligence (from Qdrant RAG):\n"
            for i, doc in enumerate(rag_docs, start=1):
                rag_context += f"[RAG-{i}] (score={doc.score:.2f}) {doc.text[:500]}\n\n"
            logger.info(
                "competitor_analysis_rag",
                hits=len(rag_docs),
                tenant_id=tenant_id,
            )
        else:
            rag_context = "## Internal Competitor Intelligence: No documents retrieved from Qdrant.\n"

        # ── Step 3: Tavily web search for live competitor profiles ─────────────
        web_query = (
            f"top competitors {sector} {target_market or geography} market share "
            f"strategic moves 2024 2025"
        )
        web_results = await self._web_search.search(web_query, max_results=5)

        # Also search for recent M&A and strategic moves
        moves_query = (
            f"{sector} {target_market or geography} acquisition partnership expansion 2024 2025"
        )
        moves_results = await self._web_search.search(moves_query, max_results=3)

        # ── Step 4: Build objective from TaskPlan ─────────────────────────────
        objective = _get_objective(task_plan, self.name)

        # ── Step 5: Assemble LLM prompt ───────────────────────────────────────
        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Agent Objective: {objective}\n\n"
            f"{watchlist_section}\n"
            f"{rag_context}\n"
            f"## Web Search — Competitor Profiles (Tavily):\n{web_results}\n\n"
            f"## Web Search — Recent Strategic Moves (Tavily):\n{moves_results}\n\n"
            "Produce the CompetitorBrief JSON now. "
            "You MUST include EXACTLY 5 five_forces entries, one per Porter force. "
            "Use the exact force name literals: supplier_power, buyer_power, "
            "competitive_rivalry, threat_of_substitution, threat_of_new_entry. "
            f"Company name is: {company_name or 'as specified in context'}. "
            f"{'Mark watchlist_sourced=true for competitors found in the WF07 watchlist cache.' if watchlist_available else ''}"
        )

        # ── Step 6: LLM call ───────────────────────────────────────────────────
        brief, tokens = await self._call_llm_json(
            SYSTEM_PROMPT,
            user_message,
            CompetitorBrief,
        )

        # ── Step 7: Update state ───────────────────────────────────────────────
        meta = self._accumulate_tokens(state, tokens)
        meta["watchlist_available"] = watchlist_available

        logger.info(
            "competitor_analysis_complete",
            company=brief.company_name,
            competitor_count=len(brief.top_competitors),
            white_space_count=len(brief.strategic_white_space),
            tokens=tokens,
        )

        return {
            **state,
            "competitor_brief": brief.model_dump(),
            "metadata": meta,
        }


def _get_objective(task_plan: dict[str, Any], agent_name: str) -> str:
    for task in task_plan.get("subtasks", []):
        if task.get("agent") == agent_name:
            return task.get("objective", "")
    return (
        "Apply Porter's Five Forces rigorously and profile the top competitors. "
        "Identify strategic white space and assess the company's competitive moat potential."
    )
