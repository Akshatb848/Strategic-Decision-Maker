"""
ASIS v3.0 — Financial Reasoning Agent.
Dissertation: McKinsey Three Horizons + NPV/IRR + Real Options Analysis.
"""
from __future__ import annotations

import json

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.mcp.financial_data import FinancialDataMCP
from asis.backend.schemas.agent_outputs import FinancialReport
from .base_agent import BaseAgent

logger = get_logger(__name__)

MASTER_PROMPT = """\
You are a specialist agent within ASIS. CRITICAL: return ONLY valid parseable JSON. \
No prose, no markdown, no backticks. Ground every finding in real-world enterprise context.\
"""

SYSTEM_PROMPT = """\
You are the ASIS Financial Reasoning Agent — a CFO-level financial strategist with deep experience \
in enterprise transformation investments. Apply McKinsey's Three Horizons framework to structure \
investment scenarios and use NPV/IRR logic to justify recommendations.

All monetary values should be realistic for the company size and industry. Use format "$Xm" or "$Xk".

Return ONLY a JSON object matching this schema:
{
  "investment_scenarios": [
    {
      "scenario": "Minimal Compliance (Horizon 1)",
      "description": "Brief description of what this scenario entails",
      "capex": "$8m",
      "opex_annual": "$3.2m",
      "risk_reduction": "28%",
      "npv_3yr": "$12m",
      "roi_3yr": "42%",
      "payback_months": 26
    },
    {
      "scenario": "Strategic Transformation (Horizon 2)",
      "description": "Brief description of what this scenario entails",
      "capex": "$22m",
      "opex_annual": "$7.5m",
      "risk_reduction": "67%",
      "npv_3yr": "$48m",
      "roi_3yr": "148%",
      "payback_months": 18
    },
    {
      "scenario": "Market Leadership (Horizon 3)",
      "description": "Brief description of what this scenario entails",
      "capex": "$40m",
      "opex_annual": "$12m",
      "risk_reduction": "85%",
      "npv_3yr": "$94m",
      "roi_3yr": "215%",
      "payback_months": 14
    }
  ],
  "cost_of_inaction": "Specific financial exposure: regulatory fines, revenue loss, client attrition estimate",
  "recommended_scenario": "Strategic Transformation (Horizon 2)",
  "recommended_budget": "$22m over 3 years",
  "revenue_protection": "Estimated $ revenue protected by proactive investment",
  "key_financial_drivers": [
    "Driver 1: specific financial lever with quantified impact",
    "Driver 2: specific financial lever with quantified impact",
    "Driver 3: specific financial lever with quantified impact"
  ],
  "payback_period": "18 months",
  "financial_risk_rating": "HIGH",
  "sensitivity_factors": [
    "Factor that could improve ROI: with scenario",
    "Factor that could worsen ROI: with scenario"
  ],
  "confidence_score": 81,
  "cfo_recommendation": "Single sentence investment recommendation with financial justification for the CFO"
}\
"""


class FinancialReasoningAgent(BaseAgent):
    name = "financial_reasoning"
    description = "McKinsey Three Horizons investment scenarios, NPV/IRR, cost-of-inaction, CFO brief."

    def __init__(self) -> None:
        super().__init__()
        self._financial_data = FinancialDataMCP()

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        task_plan = state.get("task_plan", {})
        market_report = state.get("market_report") or {}

        sector = context.get("sector", "")
        company_name = context.get("company_name") or context.get("name", "")

        await self._log(state, "info", f"[FINANCIAL REASONING] Fetching sector peer financial data from FMP — {sector}...")
        try:
            fmp_peers = await self._financial_data.get_sector_overview(sector)
        except Exception as fmp_exc:
            # FMP API unavailable (403/network) — proceed without external data
            logger.warning("fmp_skipped", sector=sector, error=str(fmp_exc)[:120])
            fmp_peers = f"FMP data unavailable — use industry benchmarks for {sector} sector."

        crm_peers = context.get("peer_companies", [])
        crm_section = ""
        if crm_peers:
            crm_section = f"## CRM Peer Companies:\n{json.dumps(crm_peers, indent=2)}\n\n"
            await self._log(state, "info", f"[FINANCIAL REASONING] CRM peer data — {len(crm_peers)} comparable firms")

        market_summary = (
            f"Market signals: {', '.join(market_report.get('market_signals', [])[:2])}\n"
            f"Opportunities: {', '.join(market_report.get('opportunities', [])[:2])}\n"
            f"Strategic implication: {market_report.get('strategic_implication', 'N/A')}"
        ) if market_report else "Market intelligence not yet available."

        await self._log(state, "info", f"[FINANCIAL REASONING] Ingesting market intelligence — building scenario assumptions...")

        objective = task_plan.get("agent_assignments", {}).get(self.name, (
            "Build McKinsey Three Horizons investment scenarios with NPV/IRR and cost-of-inaction analysis."
        ))
        await self._log(state, "info", "[FINANCIAL REASONING] Calling LLM — Three Horizons scenarios (Minimal/Strategic/Leadership), NPV, IRR, payback, CFO recommendation...")

        user_message = (
            f"Orchestrator assignment: {objective}\nProblem: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"## Market Intelligence Summary:\n{market_summary}\n\n"
            f"## FMP Sector Peer Data:\n{fmp_peers}\n\n"
            f"{crm_section}"
            f"Build financial model for {company_name} in {sector}. "
            f"{'Set crm_data_used=true since CRM peers are provided.' if crm_peers else ''} "
            "Return FinancialReport JSON now."
        )

        report, tokens = await self._call_llm_json(f"{MASTER_PROMPT}\n\n{SYSTEM_PROMPT}", user_message, FinancialReport)
        meta = self._accumulate_tokens(state, tokens)
        await self._log(state, "info", f"[FINANCIAL REASONING] Complete — Recommended: {report.recommended_scenario} | Budget: {report.recommended_budget} | Rating: {report.financial_risk_rating}")
        logger.info("financial_reasoning_complete", company=company_name, recommended=report.recommended_scenario, tokens=tokens)
        return {**state, "financial_model": report.model_dump(), "metadata": meta}
