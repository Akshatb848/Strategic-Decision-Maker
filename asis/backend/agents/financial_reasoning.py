"""
Agent 4 — Financial Reasoning
Quantitative financial analysis: market entry cost modelling,
revenue projections, ROI estimation, peer benchmarking.
Uses MCP financial data (Yahoo Finance / FMP).
"""

from __future__ import annotations

import json

from ..graph.state import AgentState
from ..mcp.financial_data import FinancialDataMCP
from .base_agent import BaseAgent
from .schemas import FinancialModel

SYSTEM_PROMPT = """\
You are a VP of Corporate Finance at a leading multinational corporation,
advising the board on a major market entry or strategic investment decision.

MANDATORY REQUIREMENTS:
1. State ALL assumptions explicitly — every number must have a stated basis.
2. Use comparable company data where available to benchmark projections.
3. Provide three-scenario revenue projections (low/base/high) for at least 3 years.
4. Do NOT fabricate financial figures — if data is unavailable, state so and provide ranges.
5. Include a disclaimer that projections are indicative.
6. All monetary values in USD millions unless otherwise stated.

Output valid JSON ONLY — no preamble, no markdown.

JSON schema:
{
  "capex_estimate_usd_mn": number_or_null,
  "opex_annual_usd_mn": number_or_null,
  "revenue_projections": [
    {"year": 2025, "low_usd_mn": 0.0, "base_usd_mn": 0.0, "high_usd_mn": 0.0}
  ],
  "roi_estimate_pct": number_or_null,
  "payback_period_years": number_or_null,
  "npv_usd_mn": number_or_null,
  "irr_pct": number_or_null,
  "comparable_firms": [
    {
      "name": "string",
      "ticker": "string_or_null",
      "revenue_usd_mn": number_or_null,
      "ebitda_margin_pct": number_or_null,
      "ev_ebitda_multiple": number_or_null,
      "notes": "string"
    }
  ],
  "assumptions": ["assumption1", "assumption2", ...],
  "sensitivity_factors": ["factor1", ...],
  "data_sources": ["source1", ...],
  "disclaimer": "string"
}
"""


class FinancialReasoningAgent(BaseAgent):
    name = "financial_reasoning"

    def __init__(self) -> None:
        super().__init__()
        self._financial_data = FinancialDataMCP()

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        task_plan = state.get("task_plan", {})
        market_report = state.get("market_report", {})

        # Fetch comparable company financial data
        sector = context.get("sector", "")
        financials = await self._financial_data.get_sector_peers(sector, limit=5)

        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Specific Objective: {_get_objective(task_plan, self.name)}\n\n"
            f"Market Context (from Market Intelligence Agent):\n"
            f"  Market Size: {market_report.get('market_size_usd_bn', 'N/A')} USD bn\n"
            f"  Growth Rate: {market_report.get('growth_rate_pct', 'N/A')}% CAGR\n"
            f"  Key Trends: {', '.join(market_report.get('key_trends', [])[:3])}\n\n"
            f"Comparable Company Financial Data:\n{financials}\n\n"
            "Produce the FinancialModel JSON now. "
            "Provide 3-year revenue projections (Year 1, 2, 3 from entry)."
        )

        model, tokens = await self._call_claude_json(
            SYSTEM_PROMPT, user_message, FinancialModel
        )

        state["financial_model"] = model.model_dump()
        self._update_token_usage(state, tokens)

        return state


def _get_objective(task_plan: dict, agent_name: str) -> str:
    for task in task_plan.get("subtasks", []):
        if task.get("agent") == agent_name:
            return task.get("objective", "")
    return "Conduct quantitative financial analysis"
