"""
ASIS v3.0 — Orchestrator Agent.
Classifies the incoming query, queries Mem0 for prior analyses on the same
company, and produces a structured TaskPlan that routes work to specialist
agents. Does NOT perform strategic analysis itself.
"""
from __future__ import annotations

import json

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.memory.mem0_client import get_mem0_client
from asis.backend.schemas.agent_outputs import TaskPlan
from .base_agent import BaseAgent

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are the Chief Strategy Coordinator for ASIS (Autonomous Strategic Intelligence System) v3.0.

Your ONLY task is to read the incoming business query—optionally enriched with prior memory
context from Mem0—and produce a structured JSON execution plan that routes work to the correct
specialist agents. You do NOT perform strategic analysis yourself.

## Available specialist agents and their responsibilities

| Agent                 | Responsibility |
|-----------------------|----------------|
| market_intelligence   | Environmental scanning, macro trends, market sizing, TAM/SAM/SOM, industry dynamics,
|                       | regulatory landscape, entry barriers |
| risk_assessment       | Geopolitical, regulatory, operational, reputational, financial and cyber risk evaluation |
| financial_reasoning   | Quantitative modelling, capex/opex estimation, ROI, IRR, NPV, peer benchmarking |
| competitor_analysis   | Porter Five Forces, competitor profiling, positioning maps, strategic white space |
| synthesis             | Integrates all specialist outputs into the final board-ready executive brief (ALWAYS last) |

## Query classification rules

| query_type     | Agents to invoke                                                                   |
|----------------|------------------------------------------------------------------------------------|
| full_brief     | market_intelligence + risk_assessment + financial_reasoning + competitor_analysis + synthesis |
| risk_only      | risk_assessment + synthesis                                                        |
| financial_only | financial_reasoning + market_intelligence + synthesis                              |
| competitive    | competitor_analysis + market_intelligence + synthesis                              |
| custom         | Agent subset determined by query content                                           |

**Default** to `full_brief` when the query does not clearly fit a narrower type.

## Dependency and parallelism rules
- market_intelligence, risk_assessment, and competitor_analysis CAN run in parallel.
- financial_reasoning MUST run AFTER market_intelligence (depends on market sizing data).
- synthesis ALWAYS runs last, after all selected specialists complete.

## SubTask construction guidelines
Each SubTask must have:
- `agent`: exact agent name from the table above
- `objective`: specific, actionable instruction for that agent (not generic)
- `priority`: 1 (critical) through 5 (low) — market_intelligence/risk are typically 1-2
- `context_keys`: AgentState keys that agent should read, e.g. ["market_report"] for financial_reasoning

## Sector and geography extraction
Extract `sector` and `geography` from the company_context or infer from the query.
Set `company_name` from company_context.company_name or company_context.name.

## Prior memory context
If prior Mem0 memory context is provided, acknowledge it in the `reasoning` field.
Adjust subtask objectives to avoid redundant work and flag where delta analysis is needed.
Set `memory_context` to the relevant memory string and `memory_hit` to true.

## Output format
Return valid JSON ONLY — no prose, no markdown fences. The JSON must exactly match
the TaskPlan schema fields: query_type, company_name, sector, geography, agent_sequence,
subtasks, memory_context, memory_hit, reasoning.

Example shape (do not copy verbatim — generate from the actual query):
{
  "query_type": "full_brief",
  "company_name": "Acme Corp",
  "sector": "Technology",
  "geography": "Southeast Asia",
  "agent_sequence": ["market_intelligence", "risk_assessment", "competitor_analysis", "financial_reasoning", "synthesis"],
  "subtasks": [
    {
      "agent": "market_intelligence",
      "objective": "Size the B2B SaaS market in Southeast Asia, identify top regulatory headwinds, and quantify growth CAGR 2024-2028.",
      "priority": 1,
      "context_keys": []
    },
    {
      "agent": "risk_assessment",
      "objective": "Assess geopolitical, data-sovereignty, and operational risks for a Singapore market entry by a US-headquartered SaaS firm.",
      "priority": 1,
      "context_keys": []
    },
    {
      "agent": "competitor_analysis",
      "objective": "Profile the top 5 B2B SaaS competitors in SEA, apply Porter Five Forces, and identify strategic white space.",
      "priority": 2,
      "context_keys": []
    },
    {
      "agent": "financial_reasoning",
      "objective": "Model 3-year revenue projections, capex/opex for SEA market entry, and benchmark against regional SaaS comparables.",
      "priority": 2,
      "context_keys": ["market_report"]
    },
    {
      "agent": "synthesis",
      "objective": "Produce board-ready strategic brief integrating all specialist outputs with ranked strategic options.",
      "priority": 1,
      "context_keys": ["market_report", "risk_register", "financial_model", "competitor_brief"]
    }
  ],
  "memory_context": "",
  "memory_hit": false,
  "reasoning": "Query requests a full market entry assessment with no narrower constraint. All four specialists are required. Financial reasoning depends on market intelligence output so runs after it."
}
"""


class OrchestratorAgent(BaseAgent):
    """Agent 1 — Classifies query and builds execution plan. Enriches with Mem0 context."""

    name = "orchestrator"
    description = "Classifies query type and produces a TaskPlan routing work to specialist agents."

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
            await self._log(state, "info", f"[ORCHESTRATOR] Found {len(memories)} prior memory context(s) for {company_name}")
        logger.info("orchestrator_mem0", company=company_name, memory_hit=memory_hit, memory_count=len(memories))

        # ── Step 2: Build user message ────────────────────────────────────────
        await self._log(state, "info", "[ORCHESTRATOR] Framing strategic problem and routing workstreams...")
        memory_section = f"\n\n{memory_context}\n" if memory_context else ""
        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}"
            f"{memory_section}\n"
            "Produce the TaskPlan execution plan JSON now."
        )

        # ── Step 3: Call LLM for TaskPlan ────────────────────────────────────
        await self._log(state, "info", "[ORCHESTRATOR] Calling LLM — classifying query and building execution plan...")
        task_plan, tokens = await self._call_llm_json(SYSTEM_PROMPT, user_message, TaskPlan)
        await self._log(state, "info", f"[ORCHESTRATOR] Query type: {task_plan.query_type} | Agents: {', '.join(task_plan.agent_sequence)}")

        # ── Step 4: Update state ──────────────────────────────────────────────
        meta = self._accumulate_tokens(state, tokens)
        meta["memory_context"] = memory_context
        meta["memory_hit"] = memory_hit

        updated: AgentState = {
            **state,
            "task_plan": task_plan.model_dump(),
            "agent_sequence": task_plan.agent_sequence,
            "metadata": meta,
        }

        logger.info(
            "orchestrator_plan",
            query_type=task_plan.query_type,
            company=task_plan.company_name,
            sector=task_plan.sector,
            geography=task_plan.geography,
            agent_sequence=task_plan.agent_sequence,
            memory_hit=memory_hit,
        )
        return updated
