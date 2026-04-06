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
    """Merge metadata dicts from parallel nodes.

    Rules:
      - sse_callback: always keep from a (set at pipeline start, never overwrite)
      - token_usage:  merge sub-dicts (each agent owns its own key)
      - total_tokens: take the max (parallel agents all started with same baseline)
      - all other keys: b wins (last writer)
    """
    merged = {**a, **b}
    # Preserve SSE callback — it's set once at pipeline start and must never be lost
    if "sse_callback" in a:
        merged["sse_callback"] = a["sse_callback"]
    # Merge per-agent token_usage dicts (not overwrite)
    merged_usage = {**a.get("token_usage", {}), **b.get("token_usage", {})}
    merged["token_usage"] = merged_usage
    # total_tokens: parallel agents each accumulated from the same baseline (orchestrator tokens).
    # Take the max rather than adding to avoid double-counting the baseline.
    merged["total_tokens"] = max(
        int(a.get("total_tokens", 0)),
        int(b.get("total_tokens", 0)),
    )
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
