"""
ASIS v3.0 — Synthesis Agent.
Dissertation: Balanced Scorecard + McKinsey 7-S + Strategic Roadmapping.
Integrates all specialist outputs into a board-ready strategic brief.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone

import httpx

from asis.backend.config.logging import get_logger
from asis.backend.graph.state import AgentState
from asis.backend.memory.mem0_client import get_mem0_client
from asis.backend.schemas.agent_outputs import SynthesisReport
from .base_agent import BaseAgent

logger = get_logger(__name__)

MASTER_PROMPT = """\
You are the most senior specialist agent within ASIS. CRITICAL: return ONLY valid parseable JSON. \
No prose, no markdown, no backticks. This output goes directly to the CEO, CFO, and Board.\
"""

SYSTEM_PROMPT = """\
You are the ASIS Synthesis Agent — the Managing Partner of Strategy. You receive intelligence reports \
from four specialist analyst teams and integrate them into a single, authoritative board-level brief.

Apply the Balanced Scorecard (Financial, Customer, Internal Process, Learning & Growth) to ensure all \
perspectives are covered. Structure the roadmap across McKinsey's Three Horizons.

Your output is what the CEO, CFO, and Board will read. It must be precise, decisive, and actionable.

Return ONLY a JSON object matching this schema:
{
  "executive_summary": "2-3 sentences: what the problem is, what analysis found, and the recommendation. Board-level precision.",
  "strategic_imperatives": [
    "Imperative 1: specific, urgent, named action with strategic rationale",
    "Imperative 2: specific, urgent, named action with strategic rationale",
    "Imperative 3: specific, urgent, named action with strategic rationale"
  ],
  "roadmap": [
    {
      "phase": "Phase 1: Foundation (0-12 months)",
      "focus": "Quick wins and risk mitigation baseline",
      "key_actions": ["Specific action 1 with named owner", "Specific action 2 with named owner"],
      "investment": "$6m",
      "success_metric": "Measurable KPI for phase completion"
    },
    {
      "phase": "Phase 2: Transformation (12-30 months)",
      "focus": "Structural redesign and capability building",
      "key_actions": ["Specific action 1 with named owner", "Specific action 2 with named owner"],
      "investment": "$10m",
      "success_metric": "Measurable KPI for phase completion"
    },
    {
      "phase": "Phase 3: Leadership (30-60 months)",
      "focus": "Competitive differentiation and sustained growth",
      "key_actions": ["Specific action 1 with named owner", "Specific action 2 with named owner"],
      "investment": "$6m",
      "success_metric": "Measurable KPI for phase completion"
    }
  ],
  "balanced_scorecard": {
    "financial": "Financial perspective: key metric and target",
    "customer": "Customer/client trust perspective: key metric and target",
    "internal_process": "Internal process perspective: key metric and target",
    "learning_growth": "People and innovation perspective: key metric and target"
  },
  "success_metrics": [
    "KPI 1: metric name, baseline, target, timeline",
    "KPI 2: metric name, baseline, target, timeline",
    "KPI 3: metric name, baseline, target, timeline"
  ],
  "decision_recommendation": "PROCEED",
  "overall_confidence": 84,
  "board_narrative": "Single unforgettable sentence that frames the strategic imperative for board vote",
  "dissertation_contribution": "One sentence articulating how this multi-agent output advances AI-driven strategic decision-making theory"
}\
"""


class SynthesisAgent(BaseAgent):
    name = "synthesis"
    description = "Balanced Scorecard synthesis, phased roadmap, board narrative, decision recommendation."

    async def run(self, state: AgentState) -> AgentState:
        query = state.get("query", "")
        context = state.get("company_context", {})
        metadata = state.get("metadata", {})
        tenant_id = self._get_tenant_id(state)
        task_plan = state.get("task_plan", {})

        company_name: str = context.get("company_name") or context.get("name") or "unknown_company"

        market_report = state.get("market_report")
        risk_register = state.get("risk_register")
        financial_model = state.get("financial_model")
        competitor_brief = state.get("competitor_brief")

        # ── Mem0 prior context ────────────────────────────────────────────────
        await self._log(state, "info", f"[SYNTHESIS] Querying Mem0 for prior ASIS recommendations — {company_name}...")
        mem0 = get_mem0_client()
        prior_memories = await mem0.search(
            query=f"strategic recommendation {company_name} {query[:80]}",
            tenant_id=tenant_id, company_name=company_name, limit=3,
        )
        prior_context = mem0.format_context(prior_memories)
        prior_memory_hit = len(prior_memories) > 0
        if prior_memory_hit:
            await self._log(state, "info", f"[SYNTHESIS] Found {len(prior_memories)} prior recommendation(s) — computing strategic delta...")

        # ── Aggregate specialist outputs ──────────────────────────────────────
        available = []
        if market_report: available.append("Market Intelligence")
        if risk_register: available.append("Risk Assessment")
        if financial_model: available.append("Financial Reasoning")
        if competitor_brief: available.append("Competitor Analysis")
        await self._log(state, "info", f"[SYNTHESIS] Aggregating specialist inputs — {' | '.join(available) if available else 'limited data'}")

        total_tokens = int(metadata.get("total_tokens", 0))
        objective = task_plan.get("agent_assignments", {}).get(self.name, (
            "Integrate all specialist outputs into a board-ready strategic brief with phased roadmap."
        ))

        memory_section = ""
        if prior_context or metadata.get("memory_context"):
            memory_section = "\n## Prior ASIS Recommendations (use for strategic delta):\n"
            if metadata.get("memory_context"):
                memory_section += metadata["memory_context"] + "\n"
            if prior_context:
                memory_section += prior_context + "\n"

        # ── LLM call ─────────────────────────────────────────────────────────
        await self._log(state, "info", f"[SYNTHESIS] Calling LLM — integrating {len(available)} specialist reports into Balanced Scorecard + phased roadmap...")
        user_message = (
            f"Orchestrator assignment: {objective}\n"
            f"All agent findings synthesised. Problem: {query}\n\n"
            f"Company Context:\n{json.dumps(context, indent=2)}\n"
            f"{memory_section}\n"
            f"=== MARKET INTELLIGENCE ===\n{json.dumps(market_report, indent=2) if market_report else 'NOT AVAILABLE'}\n\n"
            f"=== RISK REGISTER ===\n{json.dumps(risk_register, indent=2) if risk_register else 'NOT AVAILABLE'}\n\n"
            f"=== FINANCIAL MODEL ===\n{json.dumps(financial_model, indent=2) if financial_model else 'NOT AVAILABLE'}\n\n"
            f"=== COMPETITOR BRIEF ===\n{json.dumps(competitor_brief, indent=2) if competitor_brief else 'NOT AVAILABLE'}\n\n"
            f"Total tokens consumed so far: {total_tokens}\n"
            f"{'Compute memory_delta since prior context is available.' if prior_memory_hit else ''}"
            "Return SynthesisReport JSON now. Lead with the recommendation. Be decisive."
        )

        brief, tokens = await self._call_llm_json(f"{MASTER_PROMPT}\n\n{SYSTEM_PROMPT}", user_message, SynthesisReport)
        final_tokens = total_tokens + tokens
        meta = self._accumulate_tokens(state, tokens)

        await self._log(state, "info", f"[SYNTHESIS] Brief complete — Decision: {brief.decision_recommendation} | Confidence: {brief.overall_confidence}/100")
        await self._log(state, "info", f"[SYNTHESIS] Board narrative: \"{brief.board_narrative[:100]}...\"")
        await self._log(state, "info", "[SYNTHESIS] Storing to Mem0 for future cross-session continuity...")
        logger.info("synthesis_complete", company=company_name, confidence=brief.overall_confidence, decision=brief.decision_recommendation, tokens=final_tokens)

        updated: AgentState = {**state, "strategic_brief": brief.model_dump(), "metadata": meta}

        # ── Mem0 persistence (non-blocking) ───────────────────────────────────
        asyncio.ensure_future(_store_mem0(brief, tenant_id, company_name, str(state.get("analysis_id", "")), final_tokens))

        # ── n8n webhook (non-blocking) ────────────────────────────────────────
        callback_url = metadata.get("callback_url", "") or context.get("callback_url", "")
        if callback_url:
            asyncio.ensure_future(_fire_webhook(callback_url, brief, str(state.get("analysis_id", "")), tenant_id, self._settings))

        return updated


async def _store_mem0(brief: SynthesisReport, tenant_id: str, company_name: str, analysis_id: str, total_tokens: int) -> None:
    mem0 = get_mem0_client()
    memory_text = (
        f"ASIS Analysis [{analysis_id}] for {company_name}: "
        f"{brief.executive_summary[:200]} "
        f"Decision: {brief.decision_recommendation}. Confidence: {brief.overall_confidence}/100. "
        f"Board narrative: {brief.board_narrative}"
    )
    await mem0.add(
        memory_text=memory_text, tenant_id=tenant_id, company_name=company_name,
        metadata={"analysis_id": analysis_id, "confidence": brief.overall_confidence, "total_tokens": total_tokens},
    )


async def _fire_webhook(callback_url: str, brief: SynthesisReport, analysis_id: str, tenant_id: str, settings) -> None:
    payload = {
        "analysis_id": analysis_id, "tenant_id": tenant_id, "status": "completed",
        "decision_recommendation": brief.decision_recommendation,
        "overall_confidence": brief.overall_confidence,
        "executive_summary": brief.executive_summary[:400],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    secret = settings.n8n_webhook_secret.get_secret_value().encode()
    sig = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(callback_url, content=payload_bytes, headers={
                "Content-Type": "application/json", "X-ASIS-Signature": f"sha256={sig}",
                "X-ASIS-Analysis-ID": analysis_id, "X-ASIS-Timestamp": str(int(time.time())),
            })
    except Exception as exc:
        logger.warning("synthesis_webhook_failed", analysis_id=analysis_id, error=str(exc))
