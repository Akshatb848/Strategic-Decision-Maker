"""
ASIS v3.0 — Synthesis Agent.
Integrates all four specialist agent outputs into a board-ready strategic brief.

Post-completion actions (non-blocking):
  1. Stores analysis summary in Mem0 for future cross-session continuity
  2. Fires n8n completion webhook via HMAC-signed httpx POST (fire-and-forget)
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.memory.mem0_client import get_mem0_client
from asis.backend.schemas.agent_outputs import StrategicBrief
from .base_agent import BaseAgent

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are the Managing Partner of Strategy at a premier global management consultancy.
You have received intelligence reports from four specialist analyst teams and your task
is to synthesise them into a single, authoritative board-level strategic brief.

## Your mandate
Produce the definitive strategic recommendation document for the client's board and
C-suite. This brief will inform a major strategic decision. It must be internally
consistent, data-grounded, and written for senior executives who value precision over
breadth and action over analysis.

## Mandatory requirements

1. **Lead with the recommendation**: The executive_summary must open with a clear,
   unambiguous recommendation. The board should know your primary stance in the first
   two sentences. No hedging without stated reasons.

2. **Traceability**: Every claim in the brief must be traceable to a specialist report
   (market, risk, financial, or competitor). Note "per Market Intelligence Report" or
   "per Risk Register" inline where appropriate.

3. **Strategic options (minimum 2)**: Present ranked options with:
   - Specific investment estimates (in USD millions) from the financial model
   - Pros and cons grounded in the specialist report findings
   - Time-to-value in months (realistic, not optimistic)
   - Mark exactly one option as recommended=true

4. **Risk summary**: Extract and synthesise the top 3 risks from the risk register.
   State overall risk level and the single most urgent mitigation.

5. **Financial summary**: Reference the base-case NPV, IRR, and payback period.
   Acknowledge the range (low/high scenario) and key sensitivity drivers.

6. **Next steps (minimum 3)**: Each next step must be:
   - Specific and actionable (not vague)
   - Assigned to a named business function (CFO, Head of Strategy, Legal, HR, etc.)
   - Time-bound (weeks)
   - Include any dependencies

7. **Confidence and data quality scores**:
   - confidence_score (0-10): reflects how complete and consistent the specialist data is
   - data_quality_score (0-10): reflects source reliability, recency, and coverage

8. **Memory delta**: If prior ASIS analyses are provided in memory context, populate
   memory_delta with a concise description of what has changed vs. prior recommendations.
   If no prior context, set memory_delta to empty string.

9. **Agents used**: List all agents that contributed to this brief in agents_used.

10. **Caveats**: Include honest caveats where data is limited, uncertain, or where
    significant assumptions underpin the recommendation.

## Internal consistency rules
- The recommended strategic option must be consistent with the risk level
  (do not recommend aggressive expansion when overall_risk_level is "critical")
- Financial summary figures must match the financial model's base case
- Risk summary must name specific risks from the risk register (use risk_id or title)
- No contradictions between sections

## Writing style
- Board-ready language: clear, direct, no jargon without definition
- Executive summary: 200-400 words
- Each section: precise and substantive, not padded
- First person plural ("We recommend...") is acceptable and preferred

## Output format
Return valid JSON ONLY — no preamble, no markdown fences.
The JSON must exactly match the StrategicBrief schema:

{
  "company_name": "string",
  "query_summary": "string (1-2 sentence summary of the strategic question)",
  "executive_summary": "string (200+ word board-ready executive summary, opens with recommendation)",
  "recommendation": "string (100+ chars — the primary recommended course of action)",
  "strategic_options": [
    {
      "rank": 1,
      "title": "string",
      "description": "string (min 50 chars)",
      "pros": ["pro1"],
      "cons": ["con1"],
      "estimated_investment_usd_mn": number,
      "time_to_value_months": integer,
      "recommended": true|false
    }
  ],
  "risk_summary": "string (min 80 chars, refs risk register)",
  "financial_summary": "string (min 80 chars, refs NPV/IRR/payback)",
  "next_steps": [
    {
      "priority": integer 1-5,
      "action": "string (specific, actionable)",
      "owner_function": "string (e.g. CFO, Head of Strategy)",
      "timeline_weeks": integer,
      "dependencies": ["dependency1"]
    }
  ],
  "confidence_score": number 0-10,
  "data_quality_score": number 0-10,
  "sources_count": integer,
  "caveats": ["caveat1"],
  "memory_delta": "string (delta vs prior recommendations, or empty string)",
  "agents_used": ["market_intelligence", "risk_assessment", "financial_reasoning", "competitor_analysis", "synthesis"],
  "total_tokens": integer
}
"""


class SynthesisAgent(BaseAgent):
    """Agent 6 — Synthesis. Integrates all specialist outputs, queries Mem0, fires n8n webhook."""

    name = "synthesis"
    description = "Integrates all specialist outputs into a board-ready strategic brief."

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        metadata = state.get("metadata", {})
        tenant_id = self._get_tenant_id(state)

        company_name: str = (
            context.get("company_name")
            or context.get("name")
            or "unknown_company"
        )

        market_report = state.get("market_report")
        risk_register = state.get("risk_register")
        financial_model = state.get("financial_model")
        competitor_brief = state.get("competitor_brief")

        # ── Step 1: Query Mem0 for prior recommendations to same firm ──────────
        await self._log(state, "info", f"[SYNTHESIS] Querying Mem0 for prior ASIS recommendations to {company_name}...")
        mem0 = get_mem0_client()
        prior_memories = await mem0.search(
            query=f"strategic recommendation {company_name} {query[:100]}",
            tenant_id=tenant_id,
            company_name=company_name,
            limit=3,
        )
        prior_context = mem0.format_context(prior_memories)
        prior_memory_hit = len(prior_memories) > 0

        if prior_memory_hit:
            await self._log(state, "info", f"[SYNTHESIS] Found {len(prior_memories)} prior recommendation(s) in Mem0 — will compute delta vs previous analysis")
        logger.info(
            "synthesis_mem0_query",
            company=company_name,
            prior_hit=prior_memory_hit,
            count=len(prior_memories),
        )

        # ── Step 2: Aggregate sources from all specialist agents ───────────────
        await self._log(state, "info", f"[SYNTHESIS] Aggregating specialist outputs — Market: {'✓' if market_report else '✗'} | Risk: {'✓' if risk_register else '✗'} | Financial: {'✓' if financial_model else '✗'} | Competitor: {'✓' if competitor_brief else '✗'}")
        all_sources: list[str] = []
        agents_contributed: list[str] = []

        for key, report in [
            ("market_intelligence", market_report),
            ("risk_assessment", risk_register),
            ("financial_reasoning", financial_model),
            ("competitor_analysis", competitor_brief),
        ]:
            if report:
                agents_contributed.append(key)
                for src_field in ("rag_sources", "web_sources", "sources", "data_sources"):
                    src_list = report.get(src_field, [])
                    if isinstance(src_list, list):
                        for s in src_list:
                            if isinstance(s, dict):
                                all_sources.append(s.get("name", str(s)))
                            elif isinstance(s, str):
                                all_sources.append(s)

        agents_contributed.append("synthesis")
        unique_sources = sorted(set(all_sources))
        sources_count = len(unique_sources)

        # Total tokens accumulated across all agents
        total_tokens = int(metadata.get("total_tokens", 0))

        # ── Step 3: Memory context from orchestrator + synthesis Mem0 query ────
        orchestrator_memory_context = metadata.get("memory_context", "")
        memory_section = ""
        if prior_context or orchestrator_memory_context:
            memory_section = (
                "\n## Prior ASIS Recommendations (Mem0 — use for memory_delta):\n"
            )
            if orchestrator_memory_context:
                memory_section += orchestrator_memory_context + "\n"
            if prior_context and prior_context != orchestrator_memory_context:
                memory_section += prior_context + "\n"

        # ── Step 4: Build objective from TaskPlan ─────────────────────────────
        task_plan = state.get("task_plan", {})
        objective = _get_objective(task_plan, self.name)

        # ── Step 5: Assemble LLM prompt ───────────────────────────────────────
        user_message = (
            f"Strategic Query: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Agent Objective: {objective}\n"
            f"{memory_section}\n"
            f"=== MARKET INTELLIGENCE REPORT ===\n"
            f"{json.dumps(market_report, indent=2) if market_report else 'NOT AVAILABLE — exclude market_summary references'}\n\n"
            f"=== RISK REGISTER ===\n"
            f"{json.dumps(risk_register, indent=2) if risk_register else 'NOT AVAILABLE — note in caveats'}\n\n"
            f"=== FINANCIAL MODEL ===\n"
            f"{json.dumps(financial_model, indent=2) if financial_model else 'NOT AVAILABLE — note in caveats'}\n\n"
            f"=== COMPETITOR BRIEF ===\n"
            f"{json.dumps(competitor_brief, indent=2) if competitor_brief else 'NOT AVAILABLE — note in caveats'}\n\n"
            f"All Sources ({sources_count}): {unique_sources[:30]}\n"
            f"Agents Used: {agents_contributed}\n"
            f"Total Tokens Consumed: {total_tokens}\n\n"
            "Produce the StrategicBrief JSON now. "
            "Lead with the recommendation. Be specific. Be actionable. "
            f"Set total_tokens to {total_tokens} and agents_used to {json.dumps(agents_contributed)}. "
            f"Set sources_count to {sources_count}. "
            f"{'Populate memory_delta with delta vs prior recommendations.' if prior_memory_hit or metadata.get('memory_hit') else 'Set memory_delta to empty string.'}"
        )

        # ── Step 6: LLM call ───────────────────────────────────────────────────
        await self._log(state, "info", f"[SYNTHESIS] Calling LLM — integrating {len(agents_contributed)-1} specialist reports into board-ready strategic brief ({sources_count} sources, {total_tokens:,} tokens consumed so far)...")
        brief, tokens = await self._call_llm_json(
            SYSTEM_PROMPT,
            user_message,
            StrategicBrief,
        )

        # ── Step 7: Update state with final brief ─────────────────────────────
        final_tokens = total_tokens + tokens
        meta = self._accumulate_tokens(state, tokens)

        await self._log(state, "info", f"[SYNTHESIS] Strategic brief complete — Recommendation: {brief.recommendation[:100]}...")
        await self._log(state, "info", f"[SYNTHESIS] Confidence: {brief.confidence_score}/10 | Data quality: {brief.data_quality_score}/10 | {len(brief.strategic_options)} strategic options | {len(brief.next_steps)} next steps")
        await self._log(state, "info", f"[SYNTHESIS] Storing analysis to Mem0 memory for future cross-session continuity...")
        logger.info(
            "synthesis_complete",
            company=brief.company_name,
            confidence=brief.confidence_score,
            data_quality=brief.data_quality_score,
            options=len(brief.strategic_options),
            next_steps=len(brief.next_steps),
            total_tokens=final_tokens,
        )

        updated: AgentState = {
            **state,
            "strategic_brief": brief.model_dump(),
            "metadata": meta,
        }

        # ── Step 8: Store memory in Mem0 (non-blocking, best-effort) ──────────
        asyncio.ensure_future(
            _store_mem0_memory(
                brief=brief,
                tenant_id=tenant_id,
                company_name=company_name,
                analysis_id=str(state.get("analysis_id", "unknown")),
                total_tokens=final_tokens,
            )
        )

        # ── Step 9: Fire n8n completion webhook (non-blocking) ─────────────────
        callback_url: str = metadata.get("callback_url", "") or context.get("callback_url", "")
        if callback_url:
            asyncio.ensure_future(
                _fire_n8n_webhook(
                    callback_url=callback_url,
                    brief=brief,
                    analysis_id=str(state.get("analysis_id", "unknown")),
                    tenant_id=tenant_id,
                    settings=self._settings,
                )
            )

        return updated


# ── Helpers ────────────────────────────────────────────────────────────────────


def _get_objective(task_plan: dict[str, Any], agent_name: str) -> str:
    for task in task_plan.get("subtasks", []):
        if task.get("agent") == agent_name:
            return task.get("objective", "")
    return (
        "Integrate all specialist agent outputs into a board-ready strategic brief "
        "with ranked strategic options, actionable next steps, and a clear recommendation."
    )


async def _store_mem0_memory(
    brief: StrategicBrief,
    tenant_id: str,
    company_name: str,
    analysis_id: str,
    total_tokens: int,
) -> None:
    """Persist synthesis output to Mem0 for future cross-session continuity."""
    mem0 = get_mem0_client()

    # Build a concise memory string capturing the key recommendation
    recommended_options = [o for o in brief.strategic_options if o.recommended]
    top_option = recommended_options[0].title if recommended_options else (
        brief.strategic_options[0].title if brief.strategic_options else "N/A"
    )

    memory_text = (
        f"ASIS Analysis [{analysis_id}] for {company_name}: "
        f"{brief.query_summary} "
        f"Recommendation: {brief.recommendation[:200]} "
        f"Top strategic option: {top_option}. "
        f"Confidence: {brief.confidence_score}/10. "
        f"Risk summary: {brief.risk_summary[:150]} "
        f"Financial summary: {brief.financial_summary[:150]}"
    )

    success = await mem0.add(
        memory_text=memory_text,
        tenant_id=tenant_id,
        company_name=company_name,
        metadata={
            "analysis_id": analysis_id,
            "confidence_score": brief.confidence_score,
            "total_tokens": total_tokens,
            "agents_used": brief.agents_used,
        },
    )

    if success:
        logger.info(
            "synthesis_mem0_stored",
            company=company_name,
            analysis_id=analysis_id,
        )
    else:
        logger.warning(
            "synthesis_mem0_store_failed",
            company=company_name,
            analysis_id=analysis_id,
        )


async def _fire_n8n_webhook(
    callback_url: str,
    brief: StrategicBrief,
    analysis_id: str,
    tenant_id: str,
    settings: Any,
) -> None:
    """
    POST completion payload to n8n callback URL.
    Signs payload with HMAC-SHA256 using n8n_webhook_secret.
    Fire-and-forget — logs errors but does not raise.
    """
    completed_at = datetime.now(timezone.utc).isoformat()

    payload: dict[str, Any] = {
        "analysis_id": analysis_id,
        "tenant_id": tenant_id,
        "status": "completed",
        "confidence_score": brief.confidence_score,
        "executive_summary": brief.executive_summary[:500],
        "recommendation": brief.recommendation,
        "report_url": "",  # populated by API layer if available
        "completed_at": completed_at,
    }

    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    # HMAC-SHA256 signature
    secret = settings.n8n_webhook_secret.get_secret_value().encode("utf-8")
    signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-ASIS-Signature": f"sha256={signature}",
        "X-ASIS-Analysis-ID": analysis_id,
        "X-ASIS-Timestamp": str(int(time.time())),
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                callback_url,
                content=payload_bytes,
                headers=headers,
            )
            resp.raise_for_status()
            logger.info(
                "synthesis_n8n_webhook_fired",
                analysis_id=analysis_id,
                status_code=resp.status_code,
                callback_url=callback_url,
            )
    except Exception as exc:
        logger.warning(
            "synthesis_n8n_webhook_failed",
            analysis_id=analysis_id,
            callback_url=callback_url,
            error=str(exc),
        )
