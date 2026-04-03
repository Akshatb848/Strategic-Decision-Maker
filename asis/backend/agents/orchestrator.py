"""
Agent 1 — Orchestrator
Validates the incoming query, classifies it, and produces a structured
execution plan that routes tasks to the correct specialist agents.
Does NOT perform strategic analysis itself.
"""

from __future__ import annotations

import json

from ..graph.state import AgentState
from .base_agent import BaseAgent
from .schemas import TaskPlan

SYSTEM_PROMPT = """\
You are the Chief Strategy Coordinator for ASIS (Autonomous Strategic Intelligence System).

Your ONLY task is to read the incoming business query and produce a structured execution plan
that assigns subtasks to the correct specialist agents. Output valid JSON only — no prose.

Available agents and their responsibilities:
- market_intelligence: Environmental scanning, macro trends, market sizing, industry dynamics
- risk_assessment: Geopolitical, regulatory, operational, reputational risk evaluation
- financial_reasoning: Quantitative analysis, cost modelling, ROI estimation, benchmarking
- competitor_analysis: Porter Five Forces, competitor profiling, strategic white space
- synthesis: Integrates all specialist outputs into the final executive brief (ALWAYS included)

Query classification rules:
- "full": All five specialists + synthesis (default for most MNC strategic queries)
- "market_entry": market_intelligence + risk_assessment + financial_reasoning + competitor_analysis + synthesis
- "risk_only": risk_assessment + synthesis
- "financial": financial_reasoning + market_intelligence + synthesis
- "competitive": competitor_analysis + market_intelligence + synthesis

Parallel execution is possible for: market_intelligence, risk_assessment, competitor_analysis
financial_reasoning must run AFTER market_intelligence (depends on market data).
synthesis ALWAYS runs last.

Output JSON matching this schema exactly:
{
  "query_type": "full|market_entry|risk_only|financial|competitive",
  "subtasks": [
    {
      "agent": "agent_name",
      "objective": "Specific task instruction",
      "dependencies": ["agent_name_if_any"],
      "priority": 1
    }
  ],
  "agent_sequence": ["agent1", "agent2", ...],
  "parallel_agents": ["agent_that_can_run_in_parallel"],
  "reasoning": "Brief rationale (1-2 sentences)"
}
"""


class OrchestratorAgent(BaseAgent):
    name = "orchestrator"

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})

        if not query:
            state.setdefault("errors", []).append("[orchestrator] No query provided")
            return state

        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            "Produce the execution plan JSON now."
        )

        task_plan, tokens = await self._call_claude_json(
            SYSTEM_PROMPT, user_message, TaskPlan
        )

        state["task_plan"] = task_plan.model_dump()
        state["agent_sequence"] = task_plan.agent_sequence
        self._update_token_usage(state, tokens)

        return state
