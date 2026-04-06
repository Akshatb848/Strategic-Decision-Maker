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
You are the ASIS Orchestrator Agent. Your role is to decompose complex enterprise strategic questions \
into structured sub-problems and route analytical tasks to specialist agents. \
You operate as the "Chief Strategy Officer" of the pipeline.

Apply the Minto Pyramid Principle to structure the problem. Use an Issue Tree to decompose it into \
mutually exclusive, collectively exhaustive (MECE) sub-questions.

CRITICAL: Return ONLY a valid JSON object matching this EXACT schema. No text before or after. No markdown.

{
  "problem_decomposition": [
    "MECE sub-problem 1 (specific, actionable)",
    "MECE sub-problem 2 (specific, actionable)",
    "MECE sub-problem 3 (specific, actionable)",
    "MECE sub-problem 4 (specific, actionable)"
  ],
  "analytical_framework": "Primary strategic framework name and why it was selected",
  "agent_assignments": {
    "market_intelligence": "Specific research task with defined scope and output",
    "risk_assessment": "Specific risk quantification task with methodology",
    "competitor_analysis": "Specific benchmarking task with dimensions to measure",
    "financial_reasoning": "Specific financial modelling task with scenario parameters",
    "synthesis": "Integration task with deliverable specification"
  },
  "key_hypotheses": [
    "Falsifiable hypothesis 1 grounded in the problem context",
    "Falsifiable hypothesis 2 grounded in the problem context",
    "Falsifiable hypothesis 3 grounded in the problem context"
  ],
  "success_criteria": [
    "Measurable criterion 1 with metric",
    "Measurable criterion 2 with metric",
    "Measurable criterion 3 with metric"
  ],
  "confidence_score": 87,
  "strategic_priority": "HIGH",
  "time_horizon": "3-5 years",
  "dissertation_note": "One sentence connecting this decomposition to multi-agent AI theory",
  "query_type": "full_brief"
}

Additional safety instructions:
- If you are unsure about any field, provide your best reasoned estimate — never omit a field.
- If a list field requires N items, always provide exactly N items.
- Numeric scores must be integers between 0 and 100.
- The JSON must be parseable by JSON.parse() with no preprocessing.\
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
