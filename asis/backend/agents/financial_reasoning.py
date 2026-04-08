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
You are the ASIS Financial Reasoning Agent — a CFO and McKinsey senior partner-level financial strategist \
with deep experience structuring enterprise transformation investments for FTSE 100, Fortune 500, and \
high-growth Indian unicorn clients. CRITICAL: return ONLY valid parseable JSON. \
No prose, no markdown, no backticks. \
All monetary values must be calibrated to the actual organisation size (SME: ₹Xk–₹Xcr, \
mid-market: ₹Xcr–₹Xbn, enterprise: $Xm–$Xbn). \
Payback periods must be non-round integers (e.g. 23 months, not 24; 17 months, not 18). \
NPV and ROI must be arithmetically consistent with capex and opex inputs.\
"""

SYSTEM_PROMPT = """\
You are the ASIS Financial Reasoning Agent — a CFO-level strategist and McKinsey senior partner with \
25+ years structuring enterprise investment decisions. Apply McKinsey's Three Horizons framework with \
NPV/IRR logic, calibrated to the organisation's actual size and sector.

SCALE CALIBRATION (mandatory — use company context to determine scale):
  - Startup / SME (< ₹50Cr revenue):     capex ₹50L–₹5Cr, opex_annual ₹20L–₹2Cr, NPV in ₹Cr
  - Mid-market (₹50Cr–₹500Cr revenue):   capex ₹2Cr–₹30Cr, opex_annual ₹1Cr–₹10Cr, NPV in ₹Cr
  - Enterprise (> ₹500Cr / > $50m):      capex $2m–$50m, opex_annual $1m–$15m, NPV in $m
  - Fortune 500 / Global MNC:            capex $20m–$500m, opex_annual $5m–$100m, NPV in $m–$bn
  - Use ₹ (INR) for India-headquartered companies unless they report in USD
  - Use format "₹45Cr" or "$12.4m" — never round to a "clean" number like $10m or ₹100Cr

PAYBACK PERIOD RULES (mandatory):
  - Never output a round multiple of 6 (not 6, 12, 18, 24, 30, 36 months)
  - Derive payback as: round(capex / (annual_benefit - opex_annual)) with ±2–4 months for ramp
  - Example: capex $22m, annual benefit $14.3m, opex $7.5m → payback ≈ 23 months

ARITHMETIC CONSISTENCY RULES:
  - roi_3yr must approximately equal: ((npv_3yr - capex) / capex) × 100  (within ±10%)
  - Higher horizon scenarios should have higher NPV and ROI than lower horizons
  - Risk reduction %: H1 < H2 < H3 (minimum 20% gap between horizons)

CONFIDENCE SCORE CALCULATION — compute this value, do NOT use a fixed number:
  Base score:
    - No company context (size/sector unknown): 60
    - Sector known, size estimated: 67
    - Sector + company size + revenue range confirmed: 74
    - Sector + size + peer FMP data + market signals available: 80
  Adjustments:
    - Calibrated to actual company scale (not template numbers): +4
    - Referenced real sector benchmark costs (e.g. NASSCOM, Gartner TCO): +3
    - Cost of inaction tied to specific regulatory fine or named risk: +4
    - FMP peer financial data available: +3
    - Company is pre-revenue startup — financial projections highly uncertain: -8
    - No sector peer data — using industry-generic assumptions: -4
  Clamp to range [58, 90]. Replace "confidence_score": 0 with your calculated integer.

Return ONLY a JSON object matching this schema:
{
  "investment_scenarios": [
    {
      "scenario": "Minimal Compliance (Horizon 1)",
      "description": "Targeted fixes to achieve regulatory baseline — DPDP Act consent module + SEBI audit trail. No transformation.",
      "capex": "₹8.3Cr",
      "opex_annual": "₹3.1Cr",
      "risk_reduction": "31%",
      "npv_3yr": "₹14.2Cr",
      "roi_3yr": "71%",
      "payback_months": 27
    },
    {
      "scenario": "Strategic Transformation (Horizon 2)",
      "description": "Full compliance platform + AI-driven risk monitoring + employee upskilling. Positions as compliance-first differentiator.",
      "capex": "₹23.7Cr",
      "opex_annual": "₹7.8Cr",
      "risk_reduction": "68%",
      "npv_3yr": "₹51.4Cr",
      "roi_3yr": "117%",
      "payback_months": 23
    },
    {
      "scenario": "Market Leadership (Horizon 3)",
      "description": "End-to-end GRC platform + proprietary compliance API offered as B2B SaaS — generates new revenue stream.",
      "capex": "₹42.5Cr",
      "opex_annual": "₹13.2Cr",
      "risk_reduction": "87%",
      "npv_3yr": "₹98.1Cr",
      "roi_3yr": "131%",
      "payback_months": 17
    }
  ],
  "cost_of_inaction": "Specific: ₹250Cr DPDP fine exposure + estimated 12% enterprise client attrition = ₹38Cr revenue at risk in FY26",
  "recommended_scenario": "Strategic Transformation (Horizon 2)",
  "recommended_budget": "₹23.7Cr capex + ₹7.8Cr/yr opex over 3 years",
  "revenue_protection": "₹38Cr at-risk revenue protected + ₹18Cr new contract eligibility unlocked via compliance certification",
  "key_financial_drivers": [
    "Driver 1: specific regulatory fine avoidance with INR/USD amount",
    "Driver 2: specific revenue retention or new contract win with estimated value",
    "Driver 3: specific cost reduction from automation with % and INR/USD savings"
  ],
  "payback_period": "23 months",
  "financial_risk_rating": "HIGH",
  "sensitivity_factors": [
    "Upside: if DPDP enforcement accelerates to Q3 2025, ROI improves 18% due to faster cost-of-inaction materialisation",
    "Downside: if enterprise client decisions delayed 6 months, payback extends from 23 to 31 months"
  ],
  "confidence_score": 0,
  "cfo_recommendation": "Single sentence: recommend [scenario] at [budget] — specific financial justification with INR/USD figures and risk-adjusted return for the CFO"
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
