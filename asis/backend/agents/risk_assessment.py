"""
ASIS v3.0 — Risk Assessment Agent.
Dissertation: COSO ERM 2017 + ISO 31000 + NIST CSF 2.0.
Severity = Likelihood × Impact × Velocity, normalised to 100.
"""
from __future__ import annotations

import json
from typing import Any

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.mcp.news_feed import NewsFeedMCP
from asis.backend.mcp.web_search import WebSearchMCP
from asis.backend.schemas.agent_outputs import RiskReport
from .base_agent import BaseAgent

logger = get_logger(__name__)

MASTER_PROMPT = """\
You are the ASIS Risk Assessment Agent — a CRO/CISO-level analyst with deep enterprise risk management \
expertise across COSO ERM 2017, NIST CSF 2.0, and ISO 31000. CRITICAL: return ONLY valid parseable JSON. \
No prose, no markdown, no backticks. Every risk must be a specific named risk — not a category label. \
Risk owners must be actual C-suite or VP-level titles relevant to the organisation's sector. \
Severity scores must be derived from the formula: round((L×I×V)/(3×4×3)×100).\
"""

SYSTEM_PROMPT = """\
You are the ASIS Risk Assessment Agent — a Chief Risk Officer with 20+ years across financial services, \
technology, and regulated industries. Apply COSO ERM 2017 + NIST CSF 2.0 to build a board-ready risk register.

SEVERITY SCORING FORMULA (mandatory — never use arbitrary numbers):
  Severity = round((Likelihood_weight × Impact_weight × Velocity_weight) / 36 × 100)
  - Likelihood weights: High=3, Medium=2, Low=1
  - Impact weights:     Critical=4, High=3, Medium=2, Low=1
  - Velocity weights:   Immediate=3, Near-term=2, Long-term=1
  Examples: High/Critical/Immediate → round(3×4×3/36×100) = 100
            Medium/High/Near-term   → round(2×3×2/36×100) = 33  (scale up proportionally)
            High/High/Near-term     → round(3×3×2/36×100) = 50
  Add a context premium of +5 to +15 for risks with named regulatory enforcement history.

RISK SPECIFICITY REQUIREMENTS (mandatory):
  - NEVER write generic risks like "Regulatory compliance risk" — name the specific regulation
  - India fintech: "DPDP Act 2023 enforcement — data localisation non-compliance exposes ₹250Cr fine"
  - Cyber: "Third-party supply chain compromise via unpatched API gateway (CVE-class)" not "Cyber risk"
  - Talent: "Loss of licensed SEBI-certified dealers following competitor poaching" not "Talent risk"
  - Risk owner must be sector-appropriate: "VP Engineering (API Security)" not just "CTO"

CONFIDENCE SCORE CALCULATION — compute this value, do NOT use a fixed number:
  Base score:
    - Generic query, no sector/geography: 60
    - Sector known: 66
    - Sector + geography: 72
    - Sector + geography + company size + named threat context: 78
  Adjustments:
    - Named 5+ specific risks (not category labels): +4
    - Identified real regulatory enforcement precedents: +4
    - Geo-political or supply chain data available: +3
    - Board escalation threshold clearly defined: +2
    - Query is ambiguous — risk categories unclear: -6
    - No live threat intelligence available: -4
  Clamp to range [58, 90]. Replace "confidence_score": 0 with your calculated integer.

Return ONLY a JSON object matching this schema:
{
  "risk_register": [
    {
      "risk": "DPDP Act 2023 enforcement: data localisation and consent audit failure exposes ₹250Cr maximum fine",
      "category": "Regulatory",
      "likelihood": "High",
      "impact": "Critical",
      "velocity": "Near-term",
      "severity_score": 67,
      "owner": "Chief Compliance Officer / DPO",
      "current_control": "Manual consent log review — no automated data-flow mapping in place"
    },
    {
      "risk": "Specific named cyber or operational risk — not a category",
      "category": "Cyber",
      "likelihood": "High",
      "impact": "High",
      "velocity": "Immediate",
      "severity_score": 50,
      "owner": "VP Engineering (Cloud Security)",
      "current_control": "Existing control with gap identified"
    },
    {
      "risk": "Specific talent or people risk tied to organisation context",
      "category": "Talent",
      "likelihood": "Medium",
      "impact": "High",
      "velocity": "Near-term",
      "severity_score": 33,
      "owner": "Chief People Officer",
      "current_control": "Retention programme — not yet benchmarked against competitor comp packages"
    }
  ],
  "critical_risks": [
    "Risk name: specific consequence and financial exposure within 12 months",
    "Risk name: specific consequence if not addressed at board level"
  ],
  "mitigation_strategies": [
    "Strategy 1: specific control action, accountable owner, 90-day milestone, expected severity reduction from X to Y",
    "Strategy 2: specific control action, accountable owner, 90-day milestone, expected severity reduction from X to Y",
    "Strategy 3: specific control action, accountable owner, 90-day milestone, expected severity reduction from X to Y"
  ],
  "residual_risk_level": "MEDIUM",
  "risk_appetite_alignment": "Assessed against [organisation]'s stated risk appetite — specific gap or alignment noted",
  "framework_used": "COSO ERM 2017 + NIST CSF 2.0 + ISO 31000",
  "confidence_score": 0,
  "board_escalation_required": true,
  "escalation_rationale": "Specific: which risk, what threshold crossed, what decision is required from the board"
}\
"""


class RiskAssessmentAgent(BaseAgent):
    name = "risk_assessment"
    description = "COSO ERM risk register: severity scoring, mitigation strategies, board escalation."

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
        location = target_market or geography

        # GDELT cache
        gdelt_data = metadata.get("gdelt_cache", {})
        gdelt_available = bool(gdelt_data)
        gdelt_section = ""
        if gdelt_available:
            gdelt_section = "## GDELT Geopolitical Intelligence:\n" + json.dumps(gdelt_data, indent=2)[:2000] + "\n\n"
            await self._log(state, "info", f"[RISK ASSESSMENT] GDELT cache hit — geopolitical signals loaded")
        else:
            await self._log(state, "info", f"[RISK ASSESSMENT] Checking GDELT cache for {location}... (not available, using live feeds)")

        await self._log(state, "info", f"[RISK ASSESSMENT] Scanning news for political, regulatory, and cyber risk signals ({location})...")
        news_results = await self._news_feed.fetch(
            f"{location} {sector} political risk regulatory sanctions compliance 2025", max_results=5,
        )

        await self._log(state, "info", f"[RISK ASSESSMENT] Querying Tavily for operational and regulatory risk research...")
        web_results = await self._web_search.search(
            f"{location} {sector} compliance regulations cyber security operational risk 2025", max_results=5,
        )

        objective = task_plan.get("agent_assignments", {}).get(self.name, (
            "Build COSO ERM 2017 risk register across all risk categories with NIST CSF scoring."
        ))
        await self._log(state, "info", "[RISK ASSESSMENT] Calling LLM — building COSO ERM risk register (Regulatory, Cyber, Talent, Financial, Reputational, Geopolitical)...")

        user_message = (
            f"Orchestrator assignment: {objective}\nProblem: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"{gdelt_section}"
            f"## Live News Feed:\n{news_results}\n\n"
            f"## Regulatory Risk Research (Tavily):\n{web_results}\n\n"
            f"Build risk register for {company_name} in {sector} / {location}. Return RiskReport JSON now."
        )

        report, tokens = await self._call_llm_json(f"{MASTER_PROMPT}\n\n{SYSTEM_PROMPT}", user_message, RiskReport)
        meta = self._accumulate_tokens(state, tokens)
        meta["gdelt_available"] = gdelt_available

        await self._log(state, "info", f"[RISK ASSESSMENT] Complete — {len(report.risk_register)} risks | Residual level: {report.residual_risk_level} | Board escalation: {report.board_escalation_required}")
        logger.info("risk_assessment_complete", company=company_name, risk_count=len(report.risk_register), tokens=tokens)
        return {**state, "risk_register": report.model_dump(), "metadata": meta}
