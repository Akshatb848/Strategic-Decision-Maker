"""
Agent 6 — Synthesis (Strategic Brief Generator)
Integrates all five agent outputs into a single coherent executive-grade
strategic brief suitable for C-suite / board presentation.
"""

from __future__ import annotations

import json

from ..graph.state import AgentState
from .base_agent import BaseAgent
from .schemas import StrategicBrief

SYSTEM_PROMPT = """\
You are the Managing Director of Strategy at a global multinational corporation.
You have received intelligence reports from five specialist analyst teams:
Market Intelligence, Risk Assessment, Financial Reasoning, and Competitive Analysis.

Your task is to write a board-ready strategic brief.

MANDATORY REQUIREMENTS:
1. Lead with the recommendation — the executive summary must open with a clear stance.
2. Every claim must be traceable to the specialist reports provided.
3. Present 2-4 ranked strategic options with pros, cons, and investment estimates.
4. Next steps must be specific, actionable, and assigned to a responsible function.
5. Confidence score (0-10): reflects completeness and quality of underlying data.
6. Data quality score (0-10): reflects source reliability and recency.
7. Write for a C-suite audience — professional, direct, no jargon without definition.
8. The brief must be internally consistent — no contradictions between sections.

Output valid JSON ONLY — no preamble, no markdown.

JSON schema:
{
  "executive_summary": "string (200-400 words)",
  "recommendation": "string (2-3 sentences — the lead recommendation)",
  "strategic_options": [
    {
      "option_id": "OPT-001",
      "title": "string",
      "description": "string",
      "rationale": "string",
      "pros": ["pro1", "pro2"],
      "cons": ["con1", "con2"],
      "estimated_investment_usd_mn": number_or_null,
      "time_to_value": "string",
      "risk_level": "low|medium|high",
      "recommended": true_or_false
    }
  ],
  "risk_summary": "string",
  "financial_summary": "string",
  "market_summary": "string",
  "competitive_summary": "string",
  "next_steps": [
    {
      "priority": 1-10,
      "action": "string",
      "owner": "string (e.g. CFO, Head of Strategy)",
      "timeline": "string (e.g. Q3 2026)",
      "success_criteria": "string"
    }
  ],
  "confidence_score": 0.0-10.0,
  "data_quality_score": 0.0-10.0,
  "caveats": ["caveat1", ...],
  "sources": ["all_sources_cited_by_agents"]
}
"""


class SynthesisAgent(BaseAgent):
    name = "synthesis"

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})

        market_report = state.get("market_report")
        risk_register = state.get("risk_register")
        financial_model = state.get("financial_model")
        competitor_brief = state.get("competitor_brief")

        # Collect all sources from specialist agents
        all_sources: list[str] = []
        for report in [market_report, risk_register, financial_model, competitor_brief]:
            if report and isinstance(report.get("data_sources"), list):
                all_sources.extend(report["data_sources"])
            if report and isinstance(report.get("sources"), list):
                all_sources.extend(report["sources"])

        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"=== MARKET INTELLIGENCE REPORT ===\n"
            f"{json.dumps(market_report, indent=2) if market_report else 'NOT AVAILABLE'}\n\n"
            f"=== RISK REGISTER ===\n"
            f"{json.dumps(risk_register, indent=2) if risk_register else 'NOT AVAILABLE'}\n\n"
            f"=== FINANCIAL MODEL ===\n"
            f"{json.dumps(financial_model, indent=2) if financial_model else 'NOT AVAILABLE'}\n\n"
            f"=== COMPETITOR BRIEF ===\n"
            f"{json.dumps(competitor_brief, indent=2) if competitor_brief else 'NOT AVAILABLE'}\n\n"
            f"All Sources Cited: {list(set(all_sources))}\n\n"
            "Produce the StrategicBrief JSON now. "
            "Lead with the recommendation. Be specific. Be actionable."
        )

        brief, tokens = await self._call_claude_json(
            SYSTEM_PROMPT,
            user_message,
            StrategicBrief,
            max_tokens=8000,
        )

        state["strategic_brief"] = brief.model_dump()
        self._update_token_usage(state, tokens)

        return state
