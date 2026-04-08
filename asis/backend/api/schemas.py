"""
Pydantic request/response schemas for the ASIS REST API.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

# Re-export schemas defined in the shared schemas package so route modules
# can import everything from one place (from ..schemas import X)
from ..schemas.api_models import (  # noqa: F401
    N8nTriggerPayload,
    N8nTriggerResponse,
    N8nCompletionWebhook,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
)


# ── Request models ────────────────────────────────────────────────────────────


class CompanyContext(BaseModel):
    company_name: str = Field(..., description="Name of the client company")
    sector: str = Field(..., description="Industry sector (e.g. technology, healthcare)")
    target_market: str = Field(..., description="Target geography / market (e.g. India, Southeast Asia)")
    hq_country: str = Field(default="", description="HQ country")
    annual_revenue_usd_mn: Optional[float] = Field(
        None, description="Annual revenue in USD millions (optional)"
    )
    employee_count: Optional[int] = Field(None, description="Number of employees (optional)")
    additional_context: Optional[str] = Field(
        None, description="Any additional strategic context"
    )


class AnalysisOptions(BaseModel):
    include_financial: bool = True
    include_competitor: bool = True
    include_market: bool = True
    include_risk: bool = True
    run_baseline: bool = Field(
        default=False, description="Also run single-agent baseline for dissertation comparison"
    )


class CreateAnalysisRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=20,
        description="Strategic question for ASIS to analyse",
        examples=["Should we enter the Indian fintech market in 2025?"],
    )
    company_context: CompanyContext
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    organization: Optional[str] = None


# ── Response models ───────────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    full_name: Optional[str] = None
    organization: Optional[str] = None
    is_active: bool
    created_at: datetime


class AnalysisSummary(BaseModel):
    id: uuid.UUID
    query: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    execution_time_ms: Optional[int]
    confidence_score: Optional[float] = None
    data_quality_score: Optional[float] = None


class AgentRunSummary(BaseModel):
    agent_name: str
    status: str
    tokens_used: Optional[int]
    duration_ms: Optional[int]
    error_message: Optional[str]


class AnalysisDetail(AnalysisSummary):
    company_context: dict[str, Any]
    agent_runs: list[AgentRunSummary]
    strategic_brief: Optional[dict[str, Any]] = None


class ReportSummary(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    confidence_score: Optional[float]
    data_quality_score: Optional[float]
    sources_count: Optional[int]
    eval_overall_score: Optional[float]
    created_at: datetime


class EvaluationResponse(BaseModel):
    analysis_id: uuid.UUID
    analytical_depth: Optional[float]
    factual_accuracy: Optional[float]
    contextual_relevance: Optional[float]
    actionability: Optional[float]
    internal_consistency: Optional[float]
    overall_score: Optional[float]
    baseline_overall_score: Optional[float] = None
    improvement_over_baseline: Optional[float] = None


class PaginatedAnalyses(BaseModel):
    items: list[AnalysisSummary]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    redis: str = "unknown"
    qdrant: str = "unknown"
    litellm: str = "unknown"
    langfuse: str = "unknown"
    celery: str = "unknown"
    llm: str = "unknown"          # "ok" | "auth_error" | "no_api_key" | "rate_limited" | "unavailable"
    agents: dict[str, str]
