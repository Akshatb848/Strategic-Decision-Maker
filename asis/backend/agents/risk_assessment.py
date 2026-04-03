"""
Agent 3 — Risk Assessment
Geopolitical, regulatory, operational, and reputational risk evaluation.
Outputs a scored risk register. Uses MCP news feed + web search.
"""

from __future__ import annotations

import json

from ..graph.state import AgentState
from ..mcp.web_search import WebSearchMCP
from ..mcp.news_feed import NewsFeedMCP
from .base_agent import BaseAgent
from .schemas import RiskRegister

SYSTEM_PROMPT = """\
You are a Chief Risk Officer with deep expertise in cross-border MNC operations,
geopolitical risk, and enterprise risk management. You are building a risk register
for a multinational corporation making a strategic decision.

MANDATORY REQUIREMENTS:
1. Score each risk on severity (1-10) and likelihood (1-10). Risk score = severity × likelihood.
2. Every risk MUST have at least TWO concrete mitigation actions.
3. Cover all risk dimensions: geopolitical, regulatory, operational, reputational, financial, cyber.
4. Risk IDs must follow format: TYPE-NNN (e.g., GEO-001, REG-001, OPS-001).
5. Cite data sources for each risk assessment.
6. Do not fabricate events — flag uncertainty where it exists.

Output valid JSON ONLY — no preamble, no markdown.

JSON schema:
{
  "risk_items": [
    {
      "risk_id": "GEO-001",
      "risk_type": "geopolitical|regulatory|operational|reputational|financial|cyber",
      "title": "string",
      "description": "string",
      "severity": 1-10,
      "likelihood": 1-10,
      "risk_score": float (severity × likelihood),
      "time_horizon": "short (<1yr)|medium (1-3yr)|long (>3yr)",
      "mitigation": ["action1", "action2"],
      "data_sources": ["source1"]
    }
  ],
  "overall_risk_level": "low|moderate|high|critical",
  "top_risks": ["RISK-ID-1", "RISK-ID-2", "RISK-ID-3"],
  "risk_summary": "string (2-3 sentence executive summary)",
  "data_sources": ["global_source1", ...]
}
"""


class RiskAssessmentAgent(BaseAgent):
    name = "risk_assessment"

    def __init__(self) -> None:
        super().__init__()
        self._web_search = WebSearchMCP()
        self._news_feed = NewsFeedMCP()

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        task_plan = state.get("task_plan", {})

        # Gather geopolitical + regulatory news
        geo_results = await self._news_feed.fetch(
            f"{context.get('target_market', '')} political risk regulatory sanctions",
            max_results=5,
        )
        op_results = await self._web_search.search(
            f"{context.get('target_market', '')} {context.get('sector', '')} operational risk compliance",
            max_results=5,
        )

        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Specific Objective: {_get_objective(task_plan, self.name)}\n\n"
            f"Geopolitical/Regulatory News:\n{geo_results}\n\n"
            f"Operational Risk Research:\n{op_results}\n\n"
            "Produce the RiskRegister JSON now. Include at minimum 5 risks across different categories."
        )

        register, tokens = await self._call_claude_json(
            SYSTEM_PROMPT, user_message, RiskRegister
        )

        state["risk_register"] = register.model_dump()
        self._update_token_usage(state, tokens)

        return state


def _get_objective(task_plan: dict, agent_name: str) -> str:
    for task in task_plan.get("subtasks", []):
        if task.get("agent") == agent_name:
            return task.get("objective", "")
    return "Conduct comprehensive risk assessment"
