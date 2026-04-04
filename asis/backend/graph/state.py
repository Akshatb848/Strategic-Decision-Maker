"""
ASIS v3.0 shared AgentState — single source of truth for LangGraph nodes.
Every agent reads from and writes to this TypedDict (never mutates in place).
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    query: str
    company_context: dict[str, Any]
    options: dict[str, Any]

    # ── Orchestrator output ────────────────────────────────────────────────
    task_plan: Optional[dict[str, Any]]
    agent_sequence: Optional[list[str]]
    analysis_id: Optional[str]
    tenant_id: Optional[str]

    # ── Specialist agent outputs ───────────────────────────────────────────
    market_report: Optional[dict[str, Any]]
    risk_register: Optional[dict[str, Any]]
    financial_model: Optional[dict[str, Any]]
    competitor_brief: Optional[dict[str, Any]]

    # ── Final synthesis output ─────────────────────────────────────────────
    strategic_brief: Optional[dict[str, Any]]

    # ── Error accumulator ─────────────────────────────────────────────────
    errors: list[str]

    # ── Metadata (SSE callback, tokens, trace IDs, RAG hits, Mem0 context) ─
    metadata: dict[str, Any]
