"""
ASIS v3.0 — API request/response Pydantic v2 schemas.
Used by FastAPI route handlers for validation and serialisation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(min_length=8)
    tenant_slug: str = Field(
        default="default",
        description="Tenant to register under",
    )


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until expiry")
    tenant_id: str
    user_id: str
    role: str


class UserProfile(BaseModel):
    id: str
    email: str
    role: str
    tenant_id: str
    is_active: bool
    created_at: datetime


# ── Analysis ──────────────────────────────────────────────────────────────────


class CompanyContext(BaseModel):
    company_name: str = Field(min_length=1)
    sector: str = ""
    geography: str = ""
    revenue_usd_bn: float | None = None
    employees: int | None = None
    description: str = ""
    peer_companies: list[str] = Field(
        default_factory=list,
        description="Peer/comparable company names for financial benchmarking",
    )
    crm_record_id: str = Field(
        default="",
        description="CRM record ID if enriched via n8n WF06",
    )
    extra: dict[str, Any] = Field(default_factory=dict)


class AnalysisOptions(BaseModel):
    query_type: Literal[
        "full_brief", "risk_only", "financial_only", "competitive", "custom"
    ] = "full_brief"
    enable_rag: bool = True
    enable_memory: bool = True
    confidence_threshold: float = Field(ge=0.0, le=10.0, default=7.0)
    output_format: Literal["json", "markdown", "pdf"] = "json"
    run_baseline: bool = Field(
        default=False, description="Also run SingleAgentBaseline for comparison"
    )
    run_evaluation: bool = Field(
        default=True, description="Score output with EvaluationEngine"
    )


class AnalysisRequest(BaseModel):
    query: str = Field(min_length=10, max_length=2000)
    company_context: CompanyContext
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)
    tenant_id: str = Field(
        default="",
        description="Overrides JWT tenant when called via API key (n8n)",
    )


class AnalysisCreatedResponse(BaseModel):
    analysis_id: str
    status: str
    stream_url: str
    estimated_duration_seconds: int = 60


class AgentRunSummary(BaseModel):
    agent_name: str
    status: str
    duration_ms: int | None
    tokens_used: int | None
    rag_hits: int
    memory_hit: bool
    error_message: str | None


class AnalysisDetail(BaseModel):
    id: str
    query: str
    company_context: dict[str, Any]
    status: str
    created_at: datetime
    completed_at: datetime | None
    execution_time_ms: int | None
    trigger_source: str
    agent_runs: list[AgentRunSummary]
    strategic_brief: dict[str, Any] | None
    confidence_score: float | None


# ── Reports ───────────────────────────────────────────────────────────────────


class ReportSummary(BaseModel):
    id: str
    analysis_id: str
    company_name: str
    query_excerpt: str
    status: str
    confidence_score: float | None
    eval_overall_score: float | None
    created_at: datetime
    execution_time_ms: int | None


class ReportListResponse(BaseModel):
    items: list[ReportSummary]
    total: int
    page: int
    page_size: int
    has_next: bool


# ── n8n Webhooks ──────────────────────────────────────────────────────────────


class N8nTriggerPayload(BaseModel):
    workflow_id: str = Field(description="n8n workflow identifier")
    workflow_name: str = ""
    query: str = Field(min_length=5)
    company_context: CompanyContext
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)
    tenant_id: str = ""
    callback_url: str = Field(
        default="",
        description="URL for ASIS to POST completion webhook back to n8n",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class N8nTriggerResponse(BaseModel):
    analysis_id: str
    status: str = "queued"
    message: str = "Analysis queued successfully"


class N8nCompletionWebhook(BaseModel):
    """Payload ASIS POSTs back to n8n on analysis completion."""

    analysis_id: str
    tenant_id: str
    status: Literal["completed", "failed"]
    confidence_score: float | None
    executive_summary: str
    recommendation: str
    report_url: str
    completed_at: str


# ── Knowledge Ingestion ───────────────────────────────────────────────────────


class KnowledgeIngestRequest(BaseModel):
    url: str = Field(
        default="",
        description="Public URL to fetch and ingest (if no file upload)",
    )
    doc_type: Literal[
        "market_report",
        "regulatory",
        "internal_strategy",
        "competitor_intel",
        "financial",
        "general",
    ] = "general"
    sector: str = ""
    geography: str = ""
    source_label: str = ""


class KnowledgeIngestResponse(BaseModel):
    chunks_created: int
    collection: str
    tenant_id: str
    doc_type: str
    message: str


# ── Health ────────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    environment: str
    database: str
    redis: str
    qdrant: str
    litellm: str
    langfuse: str
    celery: str
    agents: dict[str, str]
