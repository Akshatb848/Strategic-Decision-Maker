"""
ASIS v3.0 — Orchestrator Agent.
Dissertation: Minto Pyramid Principle + Issue Tree decomposition.
Decomposes strategic query into MECE sub-problems and routes to specialist agents.
"""
from __future__ import annotations

import json

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.memory.mem0_client import get_mem0_client
from asis.backend.schemas.agent_outputs import OrchestratorOutput
from .base_agent import BaseAgent

logger = get_logger(__name__)

MASTER_SYSTEM_PROMPT = """\
You are a specialist agent within ASIS (Autonomous Strategic Intelligence System), \
a multi-agent AI platform built for enterprise strategic decision-making in Multinational Corporations.

CRITICAL OPERATING RULES — NEVER VIOLATE:
1. You MUST return ONLY a valid, parseable JSON object. No prose, no markdown, no backticks, no explanation before or after.
2. Every string value must be concise and specific to the problem context. No generic placeholders.
3. Every numeric field (scores, percentages, budgets) must contain a realistic, defensible number.
4. If you are uncertain about a value, provide a reasoned estimate — never leave a field empty or null.
5. Your output will be parsed programmatically. A malformed response causes system failure.
6. Ground every finding in real-world enterprise context relevant to the company and industry specified.\
"""

SYSTEM_PROMPT = """\
You are the ASIS Orchestrator Agent — the Chief Strategy Officer of the multi-agent pipeline. \
You are a senior strategic consultant with 20+ years advising Fortune 500 boards. \
Your role is to decompose complex enterprise strategic questions into structured sub-problems \
and route analytical tasks to specialist agents.

Apply the Minto Pyramid Principle: Answer First → Supporting Arguments → Evidence. \
Use an Issue Tree to decompose into MECE (Mutually Exclusive, Collectively Exhaustive) sub-questions.

First, extract from the problem statement:
  - Organisation name (if stated)
  - Industry/sector
  - Geography/market
  - Decision type: invest | divest | enter | exit | restructure | defend | partner
  - Time horizon
  - Primary constraints

The problem decomposition sub-problems must map directly to the 5 specialist agents. \
Each agent assignment must be specific — stating the exact scope, methodology, and expected output.

CONFIDENCE SCORE CALCULATION (mandatory):
  Base score: 88 if the problem clearly names an organisation AND industry AND decision type
  Base score: 78 if only 2 of the 3 above are clear
  Base score: 68 if only 1 is clear or the problem is vague
  Apply adjustments:
    -5 if the geography/market is not specified
    -8 if the decision type is ambiguous (cannot be classified above)
    +3 if specific constraints, KPIs, or deadlines are mentioned
    +2 if the problem names specific competitors or regulations
  Clamp result to [72, 93]. Round to integer.
  DO NOT output 87 or any fixed default. Calculate from the problem.

CRITICAL: Return ONLY a valid JSON object. No text before or after. No markdown. No backticks.

{
  "problem_decomposition": [
    "MECE sub-problem 1: specific question tied to market/regulatory dimensions",
    "MECE sub-problem 2: specific question tied to risk quantification",
    "MECE sub-problem 3: specific question tied to competitive positioning",
    "MECE sub-problem 4: specific question tied to financial viability"
  ],
  "analytical_framework": "Named framework (e.g. Minto Pyramid + PESTLE + COSO ERM) and why selected for THIS problem",
  "agent_assignments": {
    "market_intelligence": "Specific task: name the regulations, sectors, and geographies to analyse",
    "risk_assessment": "Specific task: name the risk categories and COSO ERM domains to assess",
    "competitor_analysis": "Specific task: name the competitor set and benchmark dimensions",
    "financial_reasoning": "Specific task: define the 3 horizon scenarios and financial metrics to model",
    "synthesis": "Specific integration task: specify the decision gate and board deliverable"
  },
  "key_hypotheses": [
    "Falsifiable hypothesis 1: specific claim about THIS organisation and market",
    "Falsifiable hypothesis 2: specific claim about risk or competitive position",
    "Falsifiable hypothesis 3: specific claim about financial return or risk"
  ],
  "success_criteria": [
    "Criterion 1: specific KPI with baseline and target (e.g. Compliance score 65% → 90%)",
    "Criterion 2: specific financial metric with target (e.g. ROI > 100% within 3 years)",
    "Criterion 3: specific operational metric with target"
  ],
  "confidence_score": 0,
  "strategic_priority": "HIGH",
  "time_horizon": "3-5 years",
  "dissertation_note": "One sentence connecting this MECE decomposition to multi-agent AI strategic decision theory",
  "query_type": "full_brief"
}

Replace confidence_score=0 with your calculated value using the formula above.
Never output 87. Never output a fixed default. Every analysis gets a different score.\
"""


class OrchestratorAgent(BaseAgent):
    """Agent 1 — Decomposes strategic query using Minto Pyramid. Enriches with Mem0 context."""

    name = "orchestrator"
    description = "Strategic decomposition, problem framing, and agent task assignment."

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "").strip()
        context = state.get("company_context", {})
        tenant_id = self._get_tenant_id(state)

        if not query:
            return {"errors": ["orchestrator: No query provided"]}  # type: ignore[return-value]

        company_name: str = (
            context.get("company_name")
            or context.get("name")
            or "unknown_company"
        )

        # ── Step 1: Query Mem0 for prior analyses ─────────────────────────────
        await self._log(state, "info", f"[ORCHESTRATOR] Searching memory context for {company_name}...")
        mem0 = get_mem0_client()
        memories = await mem0.search(
            query=query,
            tenant_id=tenant_id,
            company_name=company_name,
            limit=5,
        )
        memory_context = mem0.format_context(memories)
        memory_hit = len(memories) > 0

        if memory_hit:
            await self._log(state, "info", f"[ORCHESTRATOR] Found {len(memories)} prior analysis context(s) for {company_name}")

        # ── Step 2: Build user message ────────────────────────────────────────
        await self._log(state, "info", "[ORCHESTRATOR] Applying Minto Pyramid — decomposing strategic problem into MECE issue tree...")
        memory_section = f"\n\nPrior ASIS context for {company_name}:\n{memory_context}\n" if memory_context else ""
        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}"
            f"{memory_section}\n"
            "Produce the TaskPlan execution plan JSON now."
        )

        # ── Step 3: LLM call ──────────────────────────────────────────────────
        await self._log(state, "info", "[ORCHESTRATOR] Calling LLM — classifying query and routing to specialist agents...")
        task_plan, tokens = await self._call_llm_json(
            f"{MASTER_SYSTEM_PROMPT}\n\n{SYSTEM_PROMPT}",
            user_message,
            OrchestratorOutput,
        )
        await self._log(state, "info", f"[ORCHESTRATOR] Framework: {task_plan.analytical_framework[:80]} | Priority: {task_plan.strategic_priority} | Horizon: {task_plan.time_horizon}")

        # ── Step 4: Update state ──────────────────────────────────────────────
        meta = self._accumulate_tokens(state, tokens)
        meta["memory_context"] = memory_context
        meta["memory_hit"] = memory_hit

        logger.info(
            "orchestrator_plan",
            company=task_plan.agent_assignments.keys(),
            priority=task_plan.strategic_priority,
            memory_hit=memory_hit,
        )

        return {
            **state,
            "task_plan": task_plan.model_dump(),
            "agent_sequence": list(task_plan.agent_assignments.keys()),
            "metadata": meta,
        }
