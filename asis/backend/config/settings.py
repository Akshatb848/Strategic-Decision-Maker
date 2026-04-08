"""
ASIS v3.0 Configuration — Pydantic Settings with GCP Secret Manager support.
All secrets sourced from environment variables injected by Secret Manager bindings.
Zero hardcoded values. Zero secrets in files.
"""

from __future__ import annotations

import json as _json
from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "ASIS — Autonomous Strategic Intelligence System"
    app_version: str = "3.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── API Server ────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/v1"
    # Stored as str — pydantic-settings would JSON-pre-parse list[str] fields
    allowed_origins_raw: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("allowed_origins", "ALLOWED_ORIGINS"),
    )

    @property
    def allowed_origins(self) -> list[str]:
        v = self.allowed_origins_raw.strip()
        if not v:
            return ["http://localhost:3000"]
        if v.startswith("["):
            try:
                return _json.loads(v)
            except Exception:
                pass
        return [s.strip() for s in v.split(",") if s.strip()]

    # ── Security ──────────────────────────────────────────────────────────────
    jwt_secret: SecretStr = Field(..., description="JWT signing secret (min 32 chars)")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # n8n webhook HMAC secret
    n8n_webhook_secret: SecretStr = Field(
        default="changeme-n8n-secret-32chars-min",
        description="HMAC-SHA256 secret for n8n webhook verification",
    )

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_min_length(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        return v

    # ── Database (Cloud SQL / PostgreSQL) ─────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://asis:asis@localhost:5432/asis",
        description="Async PostgreSQL connection string (asyncpg)",
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # ── Redis / Memorystore ───────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for Celery, rate limiting, SSE channels",
    )
    rate_limit_per_minute: int = 20

    # ── LLM Backend: Groq (free, no credit card, world's fastest inference) ──
    # Sign up at groq.com → Console → API Keys → create key (gsk_...)
    # Set LLM_API_KEY=gsk_... in .env — that's the only required secret.
    llm_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="OpenAI-compatible LLM endpoint. Default: Groq free tier.",
    )
    llm_api_key: SecretStr = Field(
        default="",
        description="Groq API key (gsk_...). Free at groq.com — no credit card.",
    )

    # ── Per-agent Groq model assignments ─────────────────────────────────────
    # Each model chosen for optimal quality within Groq's free tier.

    # Orchestrator: ultra-fast 8B — query routing + MECE decomposition
    # 131K context, sub-second TTFT, ideal for structured classification tasks
    orchestrator_model: str = "llama-3.1-8b-instant"

    # Market Intelligence: best-quality 70B — PESTLE + Porter's Five Forces
    # Meta's strongest open model, excellent multi-domain research capability
    market_intel_model: str = "llama-3.3-70b-versatile"

    # Risk Assessment: DeepSeek R1 distill — chain-of-thought COSO ERM scoring
    # R1 reasoning traces produce rigorous Severity = L×I×V/36×100 calculations
    risk_model: str = "deepseek-r1-distill-llama-70b"

    # Financial Reasoning: DeepSeek R1 distill — multi-step NPV/IRR/payback math
    # R1's step-by-step arithmetic prevents hallucinated round numbers
    financial_model_name: str = "deepseek-r1-distill-llama-70b"

    # Competitor Analysis: 70B versatile — Porter gap analysis + benchmark data
    competitor_model: str = "llama-3.3-70b-versatile"

    # Synthesis: fast 8B — assembles 5 agent outputs into board-ready brief
    # Speed > raw power here: the heavy analysis is already done upstream
    synthesis_model: str = "llama-3.1-8b-instant"

    # Primary/fallback model (used when an override resolves to empty)
    claude_model: str = "llama-3.3-70b-versatile"
    # Fast/fallback model
    claude_haiku_model: str = "llama-3.1-8b-instant"

    embedding_model: str = "BAAI/bge-large-en-v1.5"
    claude_max_tokens: int = 6000

    # Legacy Anthropic key — kept so existing .env files don't break.
    anthropic_api_key: SecretStr = Field(
        default="",
        description="Legacy Anthropic API key (not used when llm_api_key is set)",
    )

    # ── LiteLLM Proxy (optional — not used in default deployment) ────────────
    # Activate to route agents to multiple providers or add paid models.
    # See litellm_config.yaml for configuration and upgrade path.
    litellm_proxy_url: str = Field(
        default="http://localhost:4000",
        description="LiteLLM proxy URL (optional). Not active in default Groq-direct mode.",
    )
    litellm_master_key: SecretStr = Field(
        default="",
        description="LiteLLM proxy master key (optional). Only needed if proxy is active.",
    )

    # ── Qdrant (Vector Store) ─────────────────────────────────────────────────
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL",
    )
    qdrant_api_key: SecretStr = Field(
        default="",
        description="Qdrant API key (leave empty for local/unauthenticated)",
    )
    qdrant_collection_prefix: str = "asis"
    qdrant_top_k: int = 5
    qdrant_score_threshold: float = 0.72

    # ── Mem0 (Episodic Memory) ────────────────────────────────────────────────
    mem0_api_key: SecretStr = Field(
        default="",
        description="Mem0 API key (cloud) or leave empty for self-hosted",
    )
    mem0_base_url: str = Field(
        default="http://localhost:8080",
        description="Mem0 self-hosted base URL",
    )

    # ── Langfuse (Observability) ──────────────────────────────────────────────
    langfuse_public_key: str = Field(default="", description="Langfuse public key")
    langfuse_secret_key: SecretStr = Field(
        default="", description="Langfuse secret key"
    )
    langfuse_host: str = Field(
        default="http://localhost:3000",
        description="Langfuse self-hosted URL",
    )
    langfuse_enabled: bool = True

    # ── OpenTelemetry ─────────────────────────────────────────────────────────
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "asis-backend"

    # ── MCP / External APIs ───────────────────────────────────────────────────
    tavily_api_key: SecretStr = Field(default="", description="Tavily search API key")
    fmp_api_key: SecretStr = Field(
        default="", description="Financial Modeling Prep API key"
    )
    newsapi_key: SecretStr = Field(default="", description="NewsAPI key")
    google_drive_credentials: str = Field(
        default="", description="Path to Google service account JSON"
    )

    # ── Celery ────────────────────────────────────────────────────────────────
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL (Memorystore in production)",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL",
    )

    # ── Agent Execution ───────────────────────────────────────────────────────
    agent_timeout_seconds: int = 120
    mcp_tool_timeout_seconds: int = 30
    mcp_retry_count: int = 2
    max_agent_retries: int = 2

    # ── Multi-tenancy ─────────────────────────────────────────────────────────
    default_tenant_id: str = "default"

    # ── Evaluation Weights ────────────────────────────────────────────────────
    eval_weight_analytical_depth: float = 0.25
    eval_weight_factual_accuracy: float = 0.25
    eval_weight_contextual_relevance: float = 0.20
    eval_weight_actionability: float = 0.20
    eval_weight_internal_consistency: float = 0.10

    @field_validator(
        "eval_weight_analytical_depth",
        "eval_weight_factual_accuracy",
        "eval_weight_contextual_relevance",
        "eval_weight_actionability",
        "eval_weight_internal_consistency",
    )
    @classmethod
    def weight_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Evaluation weights must be between 0 and 1")
        return v

    @property
    def eval_weights(self) -> dict[str, float]:
        return {
            "analytical_depth": self.eval_weight_analytical_depth,
            "factual_accuracy": self.eval_weight_factual_accuracy,
            "contextual_relevance": self.eval_weight_contextual_relevance,
            "actionability": self.eval_weight_actionability,
            "internal_consistency": self.eval_weight_internal_consistency,
        }

    # ── GCP ───────────────────────────────────────────────────────────────────
    gcp_project_id: str = Field(default="", description="GCP project ID")
    gcp_region: str = Field(default="asia-south1", description="Primary GCP region")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton. Import this everywhere."""
    return Settings()
