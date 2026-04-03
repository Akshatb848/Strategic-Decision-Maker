"""
Agent 5 — Competitor Analysis
Porter's Five Forces analysis + direct competitor profiling.
Maps competitive positioning and identifies strategic white space.
Uses MCP web search + news feed.
"""

from __future__ import annotations

import json

from ..graph.state import AgentState
from ..mcp.web_search import WebSearchMCP
from ..mcp.news_feed import NewsFeedMCP
from .base_agent import BaseAgent
from .schemas import CompetitorBrief

SYSTEM_PROMPT = """\
You are a Competitive Strategy Specialist at a top-tier strategy consultancy.
You are conducting a rigorous competitive analysis for a multinational corporation.

MANDATORY REQUIREMENTS:
1. Apply Porter's Five Forces rigorously — provide ALL five forces with numeric scores (1-10).
2. Profile the top 3 direct competitors in detail (strengths, weaknesses, recent strategic moves).
3. Identify at least 3 concrete, exploitable strategic white spaces (market gaps).
4. Support claims with data — cite sources for competitor data.
5. The positioning_map must include axis definitions and at least 3 competitors plotted.

Force names must be exactly:
- "Threat of New Entrants"
- "Bargaining Power of Suppliers"
- "Bargaining Power of Buyers"
- "Threat of Substitutes"
- "Competitive Rivalry"

Output valid JSON ONLY — no preamble, no markdown.

JSON schema:
{
  "five_forces": [
    {
      "force": "Competitive Rivalry",
      "rating": "weak|moderate|strong|very_strong",
      "score": 1-10,
      "rationale": "string",
      "key_factors": ["factor1", "factor2"]
    }
  ],
  "overall_competitive_intensity": "low|moderate|high|very_high",
  "top_competitors": [
    {
      "name": "string",
      "hq": "string",
      "founded": integer_or_null,
      "revenue_usd_mn": number_or_null,
      "market_share_pct": number_or_null,
      "strengths": ["str1"],
      "weaknesses": ["wk1"],
      "strategic_focus": "string",
      "recent_moves": ["move1"]
    }
  ],
  "positioning_map": {
    "x_axis": "axis_name",
    "y_axis": "axis_name",
    "competitors": [{"name": "string", "x": float, "y": float}]
  },
  "strategic_white_space": ["opportunity1", "opportunity2"],
  "sources": ["source1", ...]
}
"""


class CompetitorAnalysisAgent(BaseAgent):
    name = "competitor_analysis"

    def __init__(self) -> None:
        super().__init__()
        self._web_search = WebSearchMCP()
        self._news_feed = NewsFeedMCP()

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        task_plan = state.get("task_plan", {})

        sector = context.get("sector", "")
        target_market = context.get("target_market", "")

        competitor_search = await self._web_search.search(
            f"top companies {sector} {target_market} market leaders competitors",
            max_results=5,
        )
        competitor_news = await self._news_feed.fetch(
            f"{sector} {target_market} competitor strategy acquisition funding",
            max_results=5,
        )

        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Specific Objective: {_get_objective(task_plan, self.name)}\n\n"
            f"Competitor Research:\n{competitor_search}\n\n"
            f"Competitor News:\n{competitor_news}\n\n"
            "Produce the CompetitorBrief JSON now. "
            "Include EXACTLY 5 forces (one per Porter force)."
        )

        brief, tokens = await self._call_claude_json(
            SYSTEM_PROMPT, user_message, CompetitorBrief
        )

        state["competitor_brief"] = brief.model_dump()
        self._update_token_usage(state, tokens)

        return state


def _get_objective(task_plan: dict, agent_name: str) -> str:
    for task in task_plan.get("subtasks", []):
        if task.get("agent") == agent_name:
            return task.get("objective", "")
    return "Conduct Porter Five Forces and competitor analysis"
