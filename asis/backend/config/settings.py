"""
ASIS Configuration — Pydantic Settings with environment validation.
All secrets must come from environment variables. No hardcoded values.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, SecretStr, field_validator
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
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── API Server ────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = ["http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: object) -> list[str]:
        if isinstance(v, list):
            return v
        if not isinstance(v, str) or not v.strip():
            return ["http://localhost:3000"]
        v = v.strip()
        if v.startswith("["):
            import json as _json
            return _json.loads(v)
        return [s.strip() for s in v.split(",") if s.strip()]

    # ── Security ──────────────────────────────────────────────────────────────
    jwt_secret: SecretStr = Field(..., description="JWT signing secret (min 32 chars)")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://asis:asis@localhost:5432/asis",
        description="Async PostgreSQL connection string",
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_minute: int = 10

    # ── Anthropic / Claude ────────────────────────────────────────────────────
    anthropic_api_key: SecretStr = Field(
        ..., description="Anthropic API key for all Claude model calls"
    )
    claude_model: str = "claude-opus-4-6"
    claude_max_tokens: int = 16000

    # ── MCP / External APIs ───────────────────────────────────────────────────
    tavily_api_key: SecretStr = Field(
        default="", description="Tavily API key for web search MCP"
    )
    fmp_api_key: SecretStr = Field(
        default="", description="Financial Modeling Prep API key"
    )
    newsapi_key: SecretStr = Field(
        default="", description="NewsAPI key for news feed MCP"
    )
    google_drive_credentials: str = Field(
        default="", description="Path to Google Drive service-account JSON"
    )

    # ── Agent Execution ───────────────────────────────────────────────────────
    agent_timeout_seconds: int = 120
    mcp_tool_timeout_seconds: int = 30
    mcp_retry_count: int = 2
    max_agent_retries: int = 2

    # ── Evaluation Weights ────────────────────────────────────────────────────
    eval_weight_analytical_depth: float = 0.25
    eval_weight_factual_accuracy: float = 0.25
    eval_weight_contextual_relevance: float = 0.20
    eval_weight_actionability: float = 0.20
    eval_weight_internal_consistency: float = 0.10

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_min_length(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        return v

    @field_validator("eval_weight_analytical_depth", "eval_weight_factual_accuracy",
                     "eval_weight_contextual_relevance", "eval_weight_actionability",
                     "eval_weight_internal_consistency")
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance. Import this in all modules."""
    return Settings()
