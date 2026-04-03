"""
ASIS shared AgentState — the single source of truth passed through
every LangGraph node. Every agent reads from and writes to this TypedDict.
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    query: str                        # Original user strategic query
    company_context: dict[str, Any]  # Firm name, sector, target market, HQ, etc.
    options: dict[str, Any]          # User-selected analysis options

    # ── Orchestrator output ────────────────────────────────────────────────
    task_plan: Optional[dict[str, Any]]  # Structured execution plan
    agent_sequence: Optional[list[str]]  # Ordered list of agents to invoke
    analysis_id: Optional[str]           # UUID of the DB analysis record

    # ── Specialist agent outputs ───────────────────────────────────────────
    market_report: Optional[dict[str, Any]]     # Agent 2 — MarketIntelligenceReport
    risk_register: Optional[dict[str, Any]]     # Agent 3 — RiskRegister
    financial_model: Optional[dict[str, Any]]   # Agent 4 — FinancialModel
    competitor_brief: Optional[dict[str, Any]]  # Agent 5 — CompetitorBrief

    # ── Final synthesis output ─────────────────────────────────────────────
    strategic_brief: Optional[dict[str, Any]]  # Agent 6 — StrategicBrief

    # ── Error accumulator ─────────────────────────────────────────────────
    errors: list[str]

    # ── Metadata ──────────────────────────────────────────────────────────
    metadata: dict[str, Any]  # Timestamps, token usage, sources, SSE callbacks
