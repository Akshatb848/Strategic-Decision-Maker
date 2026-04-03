"""
SQLAlchemy ORM models for ASIS.
All database interactions must go through these models — no raw SQL.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


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


# ── Models ────────────────────────────────────────────────────────────────────


class User(Base):
    """Authenticated user. JWT subject is user_id."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analyses: Mapped[list["Analysis"]] = relationship(
        "Analysis", back_populates="user", cascade="all, delete-orphan"
    )


class Analysis(Base):
    """
    Top-level record for a single ASIS pipeline execution.
    One analysis → many AgentRuns → one Report.
    """

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    company_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    options: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.PENDING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_time_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="analyses")
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun", back_populates="analysis", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(
        "Report", back_populates="analysis", uselist=False, cascade="all, delete-orphan"
    )
    baseline_run: Mapped["BaselineRun | None"] = relationship(
        "BaselineRun", back_populates="analysis", uselist=False, cascade="all, delete-orphan"
    )


class AgentRun(Base):
    """
    Individual agent execution record within an analysis.
    Stores per-agent output, token usage, and timing.
    """

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.IDLE
    )
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="agent_runs")


class Report(Base):
    """
    Final StrategicBrief output for a completed analysis.
    Also stores evaluation scores and export metadata.
    """

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
    strategic_brief: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sources_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Evaluation scores (0-10 each)
    eval_analytical_depth: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_factual_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_contextual_relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_actionability: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_internal_consistency: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    exported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="report")


class BaselineRun(Base):
    """
    Single-agent baseline run for dissertation comparison.
    Processes the same query with one Claude call (no decomposition).
    """

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
    output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Evaluation scores mirroring Report
    eval_analytical_depth: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_factual_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_contextual_relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_actionability: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_internal_consistency: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="baseline_run")
