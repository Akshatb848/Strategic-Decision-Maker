"""
ASIS v3.0 SQLAlchemy ORM models.
Multi-tenant with tenant_id on every record.
PostgreSQL Row-Level Security policies declared via DDL events.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base — all models inherit from this."""


# ── Enums ─────────────────────────────────────────────────────────────────────


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"


class UserRole(str, enum.Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


# ── Models ────────────────────────────────────────────────────────────────────


class Tenant(Base):
    """
    Enterprise tenant. All other records reference tenant_id.
    Enables full Row-Level Security isolation.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(
        "ApiKey", back_populates="tenant", cascade="all, delete-orphan"
    )


class User(Base):
    """Authenticated user. JWT subject = user_id. Scoped to a tenant."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.ANALYST, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    analyses: Mapped[list["Analysis"]] = relationship(
        "Analysis", back_populates="user", cascade="all, delete-orphan"
    )


class ApiKey(Base):
    """Tenant-scoped API key for machine-to-machine auth (n8n, CI)."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="api_keys")


class Analysis(Base):
    """Top-level record for a single ASIS pipeline execution."""

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    company_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    options: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.PENDING, index=True
    )
    # LangGraph checkpoint thread_id for resumability
    checkpoint_thread_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_time_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Source: api | n8n_scheduled | n8n_webhook | n8n_monitor
    trigger_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="api"
    )

    user: Mapped["User | None"] = relationship("User", back_populates="analyses")
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun", back_populates="analysis", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(
        "Report",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )
    baseline_run: Mapped["BaselineRun | None"] = relationship(
        "BaselineRun",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="analysis", cascade="all, delete-orphan"
    )


class AgentRun(Base):
    """Per-agent execution record with RAG + Mem0 telemetry."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.IDLE
    )
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    rag_hits: Mapped[int] = mapped_column(Integer, default=0)
    memory_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    langfuse_trace_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    analysis: Mapped["Analysis"] = relationship(
        "Analysis", back_populates="agent_runs"
    )


class Report(Base):
    """Final StrategicBrief + evaluation scores for a completed analysis."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    strategic_brief: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sources_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # EvaluationEngine scores
    eval_analytical_depth: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_factual_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_contextual_relevance: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    eval_actionability: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_internal_consistency: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    eval_overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    exported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="report")


class BaselineRun(Base):
    """Single-agent baseline for dissertation Wilcoxon comparison."""

    __tablename__ = "baseline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    eval_analytical_depth: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_factual_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_contextual_relevance: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    eval_actionability: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_internal_consistency: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    eval_overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analysis: Mapped["Analysis"] = relationship(
        "Analysis", back_populates="baseline_run"
    )


class AuditLog(Base):
    """Immutable audit trail — every analysis request logged here."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    analysis: Mapped["Analysis | None"] = relationship(
        "Analysis", back_populates="audit_logs"
    )


# ── PostgreSQL Row-Level Security DDL ─────────────────────────────────────────
# These policies ensure zero cross-tenant data bleed at the database level.
# Application sets app.current_tenant_id on each connection via SET LOCAL.


def _enable_rls_on_table(target: Any, connection: Any, **kwargs: Any) -> None:
    """Enable RLS and create tenant isolation policy after table creation."""
    table_name = target.name
    if table_name in ("tenants",):
        return  # Tenants table is not tenant-scoped

    connection.execute(
        text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    )
    connection.execute(
        text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    )
    connection.execute(
        text(
            f"""
            CREATE POLICY tenant_isolation ON {table_name}
            USING (
                tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid
                OR current_setting('app.bypass_rls', TRUE) = 'true'
            )
            """
        )
    )


# Register RLS DDL events for all tenant-scoped tables
for _model in (Analysis, AgentRun, Report, BaselineRun, AuditLog, User, ApiKey):
    event.listen(_model.__table__, "after_create", _enable_rls_on_table)
