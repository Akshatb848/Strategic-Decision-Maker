"""
ASIS v3.0 — LangGraph 1.0 StateGraph.

Pipeline topology
-----------------
START → orchestrator → (conditional fanout via Send) →
    parallel: [market_intelligence, risk_assessment, competitor_analysis]
    (subset chosen by query_type) →
    financial_reasoning (when needed) →
    synthesis → END

Conditional routing from orchestrator based on task_plan["query_type"]:
  risk_only     → [risk_assessment]
  financial_only → [market_intelligence, financial_reasoning]
  competitive    → [market_intelligence, competitor_analysis]
  full_brief / custom → [market_intelligence, risk_assessment, competitor_analysis]

After parallel agents: financial_reasoning (if not financial_only already ran it),
then synthesis.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from asis.backend.graph.state import AgentState
from asis.backend.agents.orchestrator import OrchestratorAgent
from asis.backend.agents.market_intelligence import MarketIntelligenceAgent
from asis.backend.agents.risk_assessment import RiskAssessmentAgent
from asis.backend.agents.financial_reasoning import FinancialReasoningAgent
from asis.backend.agents.competitor_analysis import CompetitorAnalysisAgent
from asis.backend.agents.synthesis import SynthesisAgent
from asis.backend.config.logging import get_logger

logger = get_logger(__name__)

# ── Singleton agent instances ──────────────────────────────────────────────────

_orchestrator = OrchestratorAgent()
_market = MarketIntelligenceAgent()
_risk = RiskAssessmentAgent()
_financial = FinancialReasoningAgent()
_competitor = CompetitorAnalysisAgent()
_synthesis = SynthesisAgent()

# ── Routing configuration ──────────────────────────────────────────────────────

# Maps query_type → list of parallel agent node names to spawn
_QUERY_TYPE_PARALLEL: dict[str, list[str]] = {
    "risk_only":      ["risk_assessment"],
    "financial_only": ["market_intelligence", "financial_reasoning"],
    "competitive":    ["market_intelligence", "competitor_analysis"],
    "full_brief":     ["market_intelligence", "risk_assessment", "competitor_analysis"],
    "custom":         ["market_intelligence", "risk_assessment", "competitor_analysis"],
    # Legacy / fallback mappings kept for compatibility
    "full":           ["market_intelligence", "risk_assessment", "competitor_analysis"],
    "market_entry":   ["market_intelligence", "risk_assessment", "competitor_analysis"],
    "financial":      ["market_intelligence", "financial_reasoning"],
}

# These query types already include financial_reasoning in the parallel stage,
# so we skip a separate sequential financial_reasoning step afterwards.
_FINANCIAL_IN_PARALLEL: frozenset[str] = frozenset({"financial_only", "financial"})

# These query types require a sequential financial_reasoning step *after* parallel.
_NEEDS_SEQUENTIAL_FINANCIAL: frozenset[str] = frozenset({
    "full_brief", "custom", "full", "market_entry",
})


# ── Node functions ─────────────────────────────────────────────────────────────

async def orchestrator_node(state: AgentState) -> AgentState:
    return await _orchestrator.execute(state)


async def market_intelligence_node(state: AgentState) -> AgentState:
    return await _market.execute(state)


async def risk_assessment_node(state: AgentState) -> AgentState:
    return await _risk.execute(state)


async def financial_reasoning_node(state: AgentState) -> AgentState:
    return await _financial.execute(state)


async def competitor_analysis_node(state: AgentState) -> AgentState:
    return await _competitor.execute(state)


async def synthesis_node(state: AgentState) -> AgentState:
    return await _synthesis.execute(state)


# ── Conditional edge functions ─────────────────────────────────────────────────

def route_from_orchestrator(state: AgentState) -> list[Send]:
    """
    Fan-out from orchestrator using Send() for parallel execution.
    Each Send passes the full state to the target node.
    """
    task_plan: dict[str, Any] = state.get("task_plan") or {}
    query_type: str = task_plan.get("query_type", "full_brief")

    parallel_nodes = _QUERY_TYPE_PARALLEL.get(
        query_type,
        ["market_intelligence", "risk_assessment", "competitor_analysis"],
    )

    logger.info(
        "graph_route_orchestrator",
        query_type=query_type,
        parallel_nodes=parallel_nodes,
        analysis_id=state.get("analysis_id"),
    )

    return [Send(node, state) for node in parallel_nodes]


def route_after_parallel(state: AgentState) -> str:
    """
    After each parallel agent completes, decide whether to go to
    financial_reasoning or directly to synthesis.

    financial_reasoning runs sequentially (once) for full_brief / custom.
    For risk_only and competitive, skip straight to synthesis.
    For financial_only the financial_reasoning node already ran in parallel.
    """
    task_plan: dict[str, Any] = state.get("task_plan") or {}
    query_type: str = task_plan.get("query_type", "full_brief")

    # If financial_reasoning is still needed and wasn't part of the parallel batch
    if query_type in _NEEDS_SEQUENTIAL_FINANCIAL:
        # Only route here once — if financial_model already populated, skip
        if not state.get("financial_model"):
            return "financial_reasoning"
    return "synthesis"


# ── Graph builder ──────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    """
    Build and compile the ASIS StateGraph.

    Parameters
    ----------
    checkpointer : optional
        A LangGraph checkpointer instance (e.g. AsyncPostgresSaver or MemorySaver).
        If None, the graph runs without persistence.

    Returns
    -------
    CompiledGraph
    """
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("market_intelligence", market_intelligence_node)
    builder.add_node("risk_assessment", risk_assessment_node)
    builder.add_node("financial_reasoning", financial_reasoning_node)
    builder.add_node("competitor_analysis", competitor_analysis_node)
    builder.add_node("synthesis", synthesis_node)

    # START → orchestrator
    builder.add_edge(START, "orchestrator")

    # orchestrator → parallel fanout (via Send)
    builder.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        # Explicit path map — all possible target node names
        [
            "market_intelligence",
            "risk_assessment",
            "financial_reasoning",
            "competitor_analysis",
        ],
    )

    # Each parallel agent → financial_reasoning or synthesis
    for parallel_node in ["market_intelligence", "risk_assessment", "competitor_analysis"]:
        builder.add_conditional_edges(
            parallel_node,
            route_after_parallel,
            {
                "financial_reasoning": "financial_reasoning",
                "synthesis": "synthesis",
            },
        )

    # financial_reasoning (parallel variant) → synthesis
    # financial_reasoning (sequential) → synthesis
    builder.add_edge("financial_reasoning", "synthesis")

    # synthesis → END
    builder.add_edge("synthesis", END)

    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    return builder.compile(**compile_kwargs)


async def get_graph_with_checkpointer(db_url: str):
    """
    Build and return a compiled graph backed by AsyncPostgresSaver.

    The PostgresSaver is set up (schema initialised) before returning.
    Falls back to MemorySaver if postgres is unavailable.

    Parameters
    ----------
    db_url : str
        asyncpg-style connection URL. Automatically converted to psycopg
        format required by AsyncPostgresSaver.

    Returns
    -------
    CompiledGraph
    """
    # Convert asyncpg URL → psycopg URL that AsyncPostgresSaver expects
    psycopg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        checkpointer = AsyncPostgresSaver.from_conn_string(psycopg_url)
        await checkpointer.setup()
        logger.info("graph_checkpointer_ready", backend="postgres")
        return build_graph(checkpointer=checkpointer)
    except Exception as exc:
        logger.warning(
            "graph_checkpointer_fallback",
            error=str(exc),
            backend="memory",
        )
        from langgraph.checkpoint.memory import MemorySaver

        return build_graph(checkpointer=MemorySaver())


# ── Module-level default graph (no checkpointer) ──────────────────────────────
asis_graph = build_graph()
