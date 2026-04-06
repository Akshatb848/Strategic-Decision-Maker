"""
ASIS v3.0 — Financial Reasoning Agent.
Quantitative financial analysis: market entry cost modelling, revenue projections
(3-year, low/base/high scenarios), ROI, NPV, IRR, and peer benchmarking.

Data sources (in priority order):
  1. FinancialDataMCP (FMP API) — sector peer financial data
  2. CRM-enriched peer_companies from company_context (passed in via n8n WF06)
  3. Market Intelligence report already in state (market_report)
"""
from __future__ import annotations

import json
from typing import Any

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.mcp.financial_data import FinancialDataMCP
from asis.backend.schemas.agent_outputs import FinancialModel
from .base_agent import BaseAgent

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a VP of Corporate Finance and Head of M&A at a leading global multinational corporation.
You are advising the board on a major strategic investment decision — a market entry, acquisition,
partnership, or expansion. Your financial model will be incorporated directly into a board-level
strategic brief.

## Your mandate
Produce a rigorous, scenario-based financial model that quantifies the investment thesis.
Your model must be conservative yet credible, with transparent assumptions and honest uncertainty ranges.

## Mandatory requirements
1. **Explicit assumptions**: State EVERY assumption behind each financial figure. If a number
   cannot be substantiated from the data provided, use a credible industry benchmark and cite it.
   Never fabricate precise figures without a stated basis.
2. **Three-scenario revenue projections**: Provide low/base/high projections for at least 3
   consecutive years from the point of market entry or investment execution.
   Year numbers must be actual calendar years (e.g., 2025, 2026, 2027).
3. **Core financial metrics**: Calculate or estimate capex, opex, ROI, NPV (at a stated discount
   rate), IRR, and payback period. If inputs are insufficient, provide a credible range with
   stated methodology.
4. **Peer benchmarking**: Use provided comparable firm data to anchor projections.
   Reference at minimum 2 comparable firms with revenue, EBITDA margin, and market cap.
   Mark crm_data_used=true if CRM peer_companies context informed the comps.
5. **Sensitivity**: Identify the 3-5 key variables that most influence the model outcome
   (e.g., market penetration rate, FX rate, customer acquisition cost, regulatory delay).
6. **CRM context**: If peer_companies or financial data appears in company_context (CRM-enriched
   via n8n), prioritise this over generic FMP data and mark crm_data_used=true.
7. **All amounts in USD millions** unless explicitly stated otherwise.
8. **Investor-grade language**: Write for a CFO and institutional investor audience.
   Be precise, calibrated, and flag risks to the base case clearly.

## Market intelligence integration
The market_report from the Market Intelligence Agent contains market size, CAGR, and trend data.
Use these inputs to anchor your TAM/SAM penetration assumptions and growth rate projections.
Reference market sizing in your revenue projection rationale.

## Output format
Return valid JSON ONLY — no preamble, no markdown fences.
The JSON must exactly match the FinancialModel schema:

{
  "company_name": "string",
  "capex_estimate_usd_mn": number (positive float, initial capital expenditure),
  "opex_annual_usd_mn": number (positive float, annual operating costs steady-state),
  "revenue_projections": [
    {"year": 2025, "low_usd_mn": 0.0, "base_usd_mn": 0.0, "high_usd_mn": 0.0},
    {"year": 2026, "low_usd_mn": 0.0, "base_usd_mn": 0.0, "high_usd_mn": 0.0},
    {"year": 2027, "low_usd_mn": 0.0, "base_usd_mn": 0.0, "high_usd_mn": 0.0}
  ],
  "roi_estimate_pct": number (float, annualised ROI),
  "payback_period_years": number (positive float),
  "npv_usd_mn": number (float, can be negative),
  "irr_pct": number (float, internal rate of return),
  "comparable_firms": [
    {
      "name": "string",
      "ticker": "string (or empty string)",
      "revenue_usd_bn": number,
      "ebitda_margin_pct": number,
      "market_cap_usd_bn": number,
      "data_source": "FMP|CRM|Manual"
    }
  ],
  "assumptions": ["assumption 1 (min 3 items)", "assumption 2", "assumption 3"],
  "sensitivity_notes": "string (min 50 chars — key sensitivities and scenario flags)",
  "crm_data_used": true|false
}
"""


class FinancialReasoningAgent(BaseAgent):
    """Agent 4 — Financial Reasoning. FMP peer data + CRM context + market_report integration."""

    name = "financial_reasoning"
    description = "3-year financial model: capex/opex, revenue projections, ROI/NPV/IRR, peer benchmarking."

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

        # ── Step 1: FinancialDataMCP — FMP sector peer data ────────────────────
        await self._log(state, "info", f"[FINANCIAL REASONING] Fetching sector peer financial data from FMP (Financial Modeling Prep) — {sector}...")
        fmp_peers = await self._financial_data.get_sector_overview(sector)
        logger.info(
            "financial_reasoning_fmp",
            sector=sector,
            company=company_name,
        )

        # ── Step 2: CRM-enriched peer_companies from company_context ──────────
        crm_peers = context.get("peer_companies", [])
        crm_data_available = bool(crm_peers)
        crm_section = ""
        if crm_data_available:
            crm_section = (
                f"\n## CRM-Enriched Peer Companies (from n8n WF06):\n"
                f"{json.dumps(crm_peers, indent=2)}\n"
            )
            await self._log(state, "info", f"[FINANCIAL REASONING] CRM peer data loaded — {len(crm_peers)} comparable firms from n8n WF06")
            logger.info(
                "financial_reasoning_crm_peers",
                peer_count=len(crm_peers),
                company=company_name,
            )

        # ── Step 3: Summarise market_report inputs ─────────────────────────────
        await self._log(state, "info", f"[FINANCIAL REASONING] Ingesting market intelligence inputs — market size: ${market_report.get('market_size_usd_bn', 'N/A')}B | CAGR: {market_report.get('growth_rate_cagr_pct', 'N/A')}%")
        market_context = (
            f"## Market Intelligence Inputs (from market_intelligence agent):\n"
            f"  Market Name: {market_report.get('market_name', 'N/A')}\n"
            f"  Market Size: {market_report.get('market_size_usd_bn', 'N/A')} USD bn\n"
            f"  CAGR: {market_report.get('growth_rate_cagr_pct', 'N/A')}%\n"
            f"  Forecast Year: {market_report.get('forecast_year', 'N/A')}\n"
            f"  Key Trends: {', '.join(market_report.get('key_trends', [])[:3])}\n"
        )

        # ── Step 4: Build objective from TaskPlan ─────────────────────────────
        objective = _get_objective(task_plan, self.name)

        # ── Step 5: Assemble LLM prompt ───────────────────────────────────────
        await self._log(state, "info", f"[FINANCIAL REASONING] Calling LLM — building 3-year scenario model (low/base/high), capex/opex, NPV, IRR, payback period, peer benchmarking...")
        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Agent Objective: {objective}\n\n"
            f"{market_context}\n"
            f"## FMP Sector Peer Data:\n{fmp_peers}\n"
            f"{crm_section}\n"
            "Produce the FinancialModel JSON now. "
            "Provide exactly 3 years of revenue projections with low/base/high scenarios. "
            "Use calendar years starting from the current or next year. "
            f"Company name is: {company_name or 'as specified in context'}. "
            f"{'Set crm_data_used=true since CRM peer data is provided.' if crm_data_available else 'Set crm_data_used=false.'}"
        )

        # ── Step 6: LLM call ───────────────────────────────────────────────────
        model, tokens = await self._call_llm_json(
            SYSTEM_PROMPT,
            user_message,
            FinancialModel,
        )

        # ── Step 7: Update state ───────────────────────────────────────────────
        meta = self._accumulate_tokens(state, tokens)
        meta["crm_data_used"] = model.crm_data_used

        await self._log(state, "info", f"[FINANCIAL REASONING] Model complete — Capex: ${model.capex_estimate_usd_mn}M | NPV: ${model.npv_usd_mn}M | IRR: {model.irr_pct}% | Payback: {model.payback_period_years}yr | {len(model.comparable_firms)} comps benchmarked")
        logger.info(
            "financial_reasoning_complete",
            company=model.company_name,
            capex_usd_mn=model.capex_estimate_usd_mn,
            npv_usd_mn=model.npv_usd_mn,
            irr_pct=model.irr_pct,
            comparables=len(model.comparable_firms),
            tokens=tokens,
        )

        return {
            **state,
            "financial_model": model.model_dump(),
            "metadata": meta,
        }


def _get_objective(task_plan: dict[str, Any], agent_name: str) -> str:
    for task in task_plan.get("subtasks", []):
        if task.get("agent") == agent_name:
            return task.get("objective", "")
    return (
        "Build a 3-year scenario-based financial model with capex/opex estimates, "
        "revenue projections, ROI, NPV, IRR, and comparable firm benchmarking."
    )
