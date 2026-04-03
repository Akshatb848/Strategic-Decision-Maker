"""
Agent 2 — Market Intelligence
Environmental scanning: macro trends, market sizing, industry dynamics,
regulatory landscape. Uses MCP web search + news feed.
"""

from __future__ import annotations

import json

from ..graph.state import AgentState
from ..mcp.web_search import WebSearchMCP
from ..mcp.news_feed import NewsFeedMCP
from .base_agent import BaseAgent
from .schemas import MarketIntelligenceReport

SYSTEM_PROMPT = """\
You are a Senior Market Intelligence Analyst at a top-tier global management consulting firm
(McKinsey / BCG calibre). You are conducting a market intelligence assessment for a multinational
corporation's strategic decision.

MANDATORY REQUIREMENTS:
1. Cite every data point with a source (publication, database, report name and year).
2. Flag ALL regulatory considerations explicitly.
3. If data is unavailable or uncertain, state so explicitly — do not fabricate figures.
4. Structure output as valid JSON matching the MarketIntelligenceReport schema.
5. Be quantitative where possible (market size in USD billions, CAGR percentages).

Output valid JSON ONLY — no preamble, no markdown, no explanation outside the JSON.

JSON schema:
{
  "market_name": "string",
  "market_size_usd_bn": number_or_null,
  "growth_rate_pct": number_or_null,
  "forecast_year": integer_or_null,
  "key_trends": ["trend1", "trend2", ...],
  "market_drivers": ["driver1", ...],
  "market_barriers": ["barrier1", ...],
  "regulatory_flags": [
    {"jurisdiction": "string", "description": "string", "impact": "low|medium|high"}
  ],
  "target_segments": ["segment1", ...],
  "geographic_focus": "string",
  "data_sources": ["Source 1", "Source 2", ...],
  "analysis_limitations": ["limitation1", ...],
  "confidence": "low|medium|high"
}
"""


class MarketIntelligenceAgent(BaseAgent):
    name = "market_intelligence"

    def __init__(self) -> None:
        super().__init__()
        self._web_search = WebSearchMCP()
        self._news_feed = NewsFeedMCP()

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        task_plan = state.get("task_plan", {})

        # Gather live data from MCP tools
        search_results = await self._web_search.search(
            f"{context.get('target_market', '')} market size trends regulatory {context.get('sector', '')}",
            max_results=5,
        )
        news_results = await self._news_feed.fetch(
            f"{context.get('target_market', '')} {context.get('sector', '')} industry news",
            max_results=5,
        )

        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Specific Objective: {_get_objective(task_plan, self.name)}\n\n"
            f"Web Search Results:\n{search_results}\n\n"
            f"News Context:\n{news_results}\n\n"
            "Produce the MarketIntelligenceReport JSON now."
        )

        report, tokens = await self._call_claude_json(
            SYSTEM_PROMPT, user_message, MarketIntelligenceReport
        )

        state["market_report"] = report.model_dump()
        self._update_token_usage(state, tokens)

        return state


def _get_objective(task_plan: dict, agent_name: str) -> str:
    for task in task_plan.get("subtasks", []):
        if task.get("agent") == agent_name:
            return task.get("objective", "")
    return "Conduct comprehensive market intelligence analysis"
