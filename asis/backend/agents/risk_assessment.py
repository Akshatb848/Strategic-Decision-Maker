"""
ASIS v3.0 — Risk Assessment Agent.
Geopolitical, regulatory, operational, reputational, financial, and cyber risk evaluation.
Outputs a scored risk register.

Data sources (in priority order):
  1. GDELT cache — pre-loaded by n8n workflow into state metadata
  2. NewsAPI (NewsFeedMCP) — fallback for recent event coverage
  3. Tavily web search (WebSearchMCP) — regulatory and operational risk research
"""
from __future__ import annotations

import json
from typing import Any

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.mcp.news_feed import NewsFeedMCP
from asis.backend.mcp.web_search import WebSearchMCP
from asis.backend.schemas.agent_outputs import RiskRegister
from .base_agent import BaseAgent

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a Chief Risk Officer with deep expertise in cross-border MNC operations,
geopolitical risk intelligence (GDELT, Oxford Analytica calibre), and enterprise
risk management frameworks (ISO 31000, COSO ERM).

You are building a comprehensive risk register for a multinational corporation making
a significant strategic decision. Your output will be reviewed by the board risk committee.

## Your mandate
Produce a complete, scored risk register across ALL six risk dimensions. This register
feeds the synthesis agent's strategic brief and directly shapes the recommendation.

## Mandatory requirements
1. **Coverage**: Include at minimum 3 risk items spanning at least 3 different categories
   (geopolitical, regulatory, operational, financial, reputational, cyber).
2. **Scoring rigor**: Score EVERY risk on:
   - severity (1-10): business impact if the risk materialises
   - likelihood (1-10): probability of occurrence within relevant time horizon
   - risk_score: severity × likelihood (range 1.0-100.0, allow rounding)
3. **Mitigations**: Every risk MUST have at least 2 concrete, actionable mitigation strategies.
   Mitigations must be specific to the company's context — not generic platitudes.
4. **Time horizons**: Classify each risk as immediate (<6mo), short_term (6mo-1yr),
   medium_term (1-3yr), or long_term (3yr+).
5. **GDELT sourcing**: If GDELT cache data is provided, use it as the primary source for
   geopolitical and conflict-related risks. Mark gdelt_sourced=true for those risks.
6. **Top risks**: Identify the 1-3 highest risk_score items in top_risk_ids.
7. **Executive summary**: Write 150+ words summarising the overall risk picture,
   risk tolerance implications, and the single most urgent mitigation action.
8. **No fabrication**: If specific event data is unavailable, use known structural risk factors
   for the sector/geography and state the basis clearly.

## Risk category definitions
- geopolitical: Trade wars, sanctions, political instability, border disputes, regime change
- regulatory: Licensing, compliance mandates, data localisation, antitrust, sector reform
- operational: Supply chain, technology failure, talent, process, third-party dependency
- financial: FX, liquidity, credit, commodity price, interest rate, valuation risk
- reputational: Brand damage, ESG, social media, leadership controversy, customer trust
- cyber: Data breach, ransomware, IP theft, critical infrastructure attack, AI adversarial

## Output format
Return valid JSON ONLY — no preamble, no markdown fences.
The JSON must exactly match the RiskRegister schema:

{
  "company_name": "string",
  "assessment_scope": "string — what strategic decision or market is being assessed",
  "risk_items": [
    {
      "risk_id": "string (e.g. geopolitical_us_china_tariffs)",
      "category": "geopolitical|regulatory|operational|financial|reputational|cyber",
      "title": "string (concise risk title)",
      "description": "string (min 50 chars — explain the risk mechanism and business impact)",
      "severity": integer 1-10,
      "likelihood": integer 1-10,
      "risk_score": float (severity × likelihood, 1.0-100.0),
      "mitigations": ["specific mitigation 1", "specific mitigation 2"],
      "time_horizon": "immediate|short_term|medium_term|long_term",
      "gdelt_sourced": true|false
    }
  ],
  "overall_risk_level": "low|moderate|high|critical",
  "executive_risk_summary": "string (150+ word executive summary)",
  "top_risk_ids": ["risk_id_1", "risk_id_2"]
}
"""


class RiskAssessmentAgent(BaseAgent):
    """Agent 3 — Risk Assessment. GDELT cache + NewsAPI fallback + Tavily for regulatory."""

    name = "risk_assessment"
    description = "Geopolitical, regulatory, operational, financial, reputational, and cyber risk register."

    def __init__(self) -> None:
        super().__init__()
        self._news_feed = NewsFeedMCP()
        self._web_search = WebSearchMCP()

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        task_plan = state.get("task_plan", {})
        metadata = state.get("metadata", {})

        sector = context.get("sector", "")
        target_market = context.get("target_market", "")
        geography = context.get("geography", "")
        company_name = context.get("company_name") or context.get("name", "")

        # ── Step 1: Read GDELT cache from metadata (pre-loaded by n8n) ─────────
        gdelt_data = metadata.get("gdelt_cache", {})
        gdelt_context = ""
        gdelt_available = bool(gdelt_data)

        if gdelt_available:
            gdelt_context = (
                "## GDELT Geopolitical Intelligence Cache (from n8n pre-load):\n"
                + json.dumps(gdelt_data, indent=2)[:3000]
                + "\n"
            )
            logger.info(
                "risk_assessment_gdelt_hit",
                company=company_name,
                geography=geography,
            )
        else:
            gdelt_context = (
                "## GDELT Cache: Not available — using live news feeds as fallback.\n"
            )
            logger.info(
                "risk_assessment_gdelt_miss",
                company=company_name,
                geography=geography,
            )

        # ── Step 2: NewsFeedMCP fallback for recent risk events ────────────────
        news_query = (
            f"{target_market or geography} {sector} political risk regulatory sanctions "
            f"compliance 2024 2025"
        )
        news_results = await self._news_feed.fetch(news_query, max_results=5)

        # ── Step 3: Tavily for regulatory/operational risk research ────────────
        reg_query = (
            f"{target_market or geography} {sector} operational risk compliance regulations "
            f"data privacy cyber security 2024"
        )
        web_results = await self._web_search.search(reg_query, max_results=5)

        # ── Step 4: Build objective from TaskPlan ─────────────────────────────
        objective = _get_objective(task_plan, self.name)

        # ── Step 5: Assemble LLM prompt ───────────────────────────────────────
        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Agent Objective: {objective}\n\n"
            f"{gdelt_context}\n"
            f"## Live News Feed (NewsAPI fallback):\n{news_results}\n\n"
            f"## Regulatory & Operational Risk Research (Tavily):\n{web_results}\n\n"
            "Produce the RiskRegister JSON now. "
            "Ensure minimum 3 risk items across at least 3 different categories. "
            f"Mark gdelt_sourced=true for any risks drawn directly from the GDELT cache. "
            f"Company name is: {company_name or 'as specified in context'}."
        )

        # ── Step 6: LLM call ───────────────────────────────────────────────────
        register, tokens = await self._call_llm_json(
            SYSTEM_PROMPT,
            user_message,
            RiskRegister,
        )

        # ── Step 7: Update state ───────────────────────────────────────────────
        meta = self._accumulate_tokens(state, tokens)
        meta["gdelt_available"] = gdelt_available

        logger.info(
            "risk_assessment_complete",
            company=register.company_name,
            overall_risk_level=register.overall_risk_level,
            risk_count=len(register.risk_items),
            top_risks=register.top_risk_ids,
            tokens=tokens,
        )

        return {
            **state,
            "risk_register": register.model_dump(),
            "metadata": meta,
        }


def _get_objective(task_plan: dict[str, Any], agent_name: str) -> str:
    for task in task_plan.get("subtasks", []):
        if task.get("agent") == agent_name:
            return task.get("objective", "")
    return (
        "Conduct a comprehensive risk assessment across all six risk dimensions: "
        "geopolitical, regulatory, operational, financial, reputational, and cyber."
    )
