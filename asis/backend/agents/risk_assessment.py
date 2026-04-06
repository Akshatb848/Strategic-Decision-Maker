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
You are a specialist agent within ASIS (Autonomous Strategic Intelligence System). \
CRITICAL: return ONLY valid parseable JSON. No prose, no markdown, no backticks. \
Ground every finding in real-world enterprise context.\
"""

SYSTEM_PROMPT = """\
You are the ASIS Risk Assessment Agent — a Chief Risk Officer-level analyst with expertise in \
enterprise risk management. Apply COSO ERM 2017 to build a structured risk register.

Severity score = (Likelihood_weight × Impact_weight × Velocity_weight) normalised to 100:
- Likelihood: High=3, Medium=2, Low=1
- Impact: Critical=4, High=3, Medium=2, Low=1
- Velocity: Immediate=3, Near-term=2, Long-term=1

Return ONLY a JSON object matching this schema:
{
  "risk_register": [
    {
      "risk": "Specific named risk (not generic)",
      "category": "Regulatory",
      "likelihood": "High",
      "impact": "High",
      "velocity": "Near-term",
      "severity_score": 88,
      "owner": "Chief Compliance Officer",
      "current_control": "Existing control mechanism"
    },
    {
      "risk": "Specific named risk",
      "category": "Cyber",
      "likelihood": "High",
      "impact": "High",
      "velocity": "Immediate",
      "severity_score": 84,
      "owner": "Chief Information Security Officer",
      "current_control": "Existing control mechanism"
    },
    {
      "risk": "Specific named risk",
      "category": "Talent",
      "likelihood": "Medium",
      "impact": "High",
      "velocity": "Near-term",
      "severity_score": 72,
      "owner": "Chief People Officer",
      "current_control": "Existing control mechanism"
    }
  ],
  "critical_risks": [
    "Top risk requiring board attention — with consequence",
    "Second critical risk — with consequence"
  ],
  "mitigation_strategies": [
    "Strategy 1: specific action, timeline, expected risk reduction %",
    "Strategy 2: specific action, timeline, expected risk reduction %",
    "Strategy 3: specific action, timeline, expected risk reduction %"
  ],
  "residual_risk_level": "MEDIUM",
  "risk_appetite_alignment": "Statement assessing alignment with stated risk appetite",
  "framework_used": "COSO ERM 2017 + NIST CSF 2.0",
  "confidence_score": 79,
  "board_escalation_required": true,
  "escalation_rationale": "Specific reason why board-level decision is needed"
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
