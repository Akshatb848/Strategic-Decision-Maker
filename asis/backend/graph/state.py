"""
ASIS v3.0 shared AgentState — single source of truth for LangGraph nodes.

All fields that parallel nodes may write use Annotated reducers so LangGraph
can merge concurrent outputs without raising INVALID_CONCURRENT_GRAPH_UPDATE.

  - Scalar pass-through fields (query, company_context, …): _keep_last
    → parallel nodes return the same value they received; last-write wins.
  - errors list: operator.add  → appends from each node.
  - metadata dict: _merge_meta → shallow-merges, accumulates token counts.
"""

from __future__ import annotations

import operator
from typing import Any, Optional
from typing_extensions import Annotated, TypedDict


def _keep_last(a: Any, b: Any) -> Any:
    """Reducer for pass-through fields: accept the newer value."""
    return b if b is not None else a


def _merge_meta(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Merge metadata dicts; accumulate token counts; preserve SSE callback from a."""
    merged = {**a, **b}
    merged["total_tokens"] = int(a.get("total_tokens", 0)) + int(b.get("total_tokens", 0))
    # Always preserve the SSE callback from the initial state (set by analysis route)
    if "sse_callback" in a and "sse_callback" not in b:
        merged["sse_callback"] = a["sse_callback"]
    elif "sse_callback" in a:
        merged["sse_callback"] = a["sse_callback"]
    return merged


class AgentState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    query: Annotated[str, _keep_last]
    company_context: Annotated[dict[str, Any], _keep_last]
    options: Annotated[dict[str, Any], _keep_last]

    # ── Orchestrator output ────────────────────────────────────────────────
    task_plan: Annotated[Optional[dict[str, Any]], _keep_last]
    agent_sequence: Annotated[Optional[list[str]], _keep_last]
    analysis_id: Annotated[Optional[str], _keep_last]
    tenant_id: Annotated[Optional[str], _keep_last]

    # ── Specialist agent outputs ───────────────────────────────────────────
    market_report: Annotated[Optional[dict[str, Any]], _keep_last]
    risk_register: Annotated[Optional[dict[str, Any]], _keep_last]
    financial_model: Annotated[Optional[dict[str, Any]], _keep_last]
    competitor_brief: Annotated[Optional[dict[str, Any]], _keep_last]

    # ── Final synthesis output ─────────────────────────────────────────────
    strategic_brief: Annotated[Optional[dict[str, Any]], _keep_last]

    # ── Error accumulator — appended by each failing node ─────────────────
    errors: Annotated[list[str], operator.add]

    # ── Metadata (SSE callback, tokens, trace IDs, RAG hits, Mem0 context) ─
    metadata: Annotated[dict[str, Any], _merge_meta]
