import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Identified, Timestamped
from .auth import User
from .job import JobDescription, Requirement
from .resume import Finding, Resume, TextSpan


class MatchRunState(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MatchType(StrEnum):
    DIRECT = "direct"
    ADJACENT = "adjacent"
    NONE = "none"


class PromptVersion(Identified, Timestamped, Base):
    """A versioned system prompt template for reproducible extraction and matching."""

    __tablename__ = "prompt_versions"

    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    template: Mapped[str] = mapped_column(Text)
    template_sha256: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64))


class MatchRun(Identified, Timestamped, Base):
    """An evaluation of a resume against a job description under prompt and scoring versions."""

    __tablename__ = "match_runs"
    __table_args__ = (
        Index(
            "ix_match_runs_dedup",
            "resume_id",
            "job_description_id",
            "prompt_version_id",
            "scoring_version",
            unique=True,
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    job_description_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True
    )
    state: Mapped[MatchRunState] = mapped_column(String(16), default=MatchRunState.QUEUED)
    model: Mapped[str] = mapped_column(String(64))
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="SET NULL"), default=None
    )
    scoring_version: Mapped[str] = mapped_column(String(32))
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    score_if_trusted: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    impact_delta: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    requirement_count: Mapped[int | None] = mapped_column(Integer, default=None)
    unmet_required_count: Mapped[int | None] = mapped_column(Integer, default=None)
    input_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    output_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), default=None)
    latency_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    narrative: Mapped[str | None] = mapped_column(Text, default=None)
    failure_code: Mapped[str | None] = mapped_column(String(32), default=None)

    user: Mapped[User] = relationship()
    resume: Mapped[Resume] = relationship()
    job_description: Mapped[JobDescription] = relationship()
    prompt_version: Mapped[PromptVersion | None] = relationship()
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="match_run", cascade="all, delete-orphan"
    )


class Claim(Identified, Timestamped, Base):
    """A model judgement deciding whether and how a requirement is satisfied by the resume."""

    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint(
            "met = false OR primary_evidence_span_id IS NOT NULL",
            name="ck_claims_met_has_primary_evidence",
        ),
        Index("ix_claims_match_requirement", "match_run_id", "requirement_id", unique=True),
    )

    match_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("match_runs.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), index=True
    )
    met: Mapped[bool] = mapped_column(Boolean)
    match_type: Mapped[MatchType] = mapped_column(String(16))
    satisfaction: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    corroboration: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    integrity_factor: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    evidence_quality: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    weight_applied: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    contribution: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    primary_evidence_span_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("text_spans.id", ondelete="SET NULL"), default=None
    )
    rationale: Mapped[str | None] = mapped_column(Text, default=None)
    adjacency_note: Mapped[str | None] = mapped_column(Text, default=None)

    match_run: Mapped[MatchRun] = relationship(back_populates="claims")
    requirement: Mapped[Requirement] = relationship()
    primary_evidence_span: Mapped[TextSpan | None] = relationship()
    evidence: Mapped[list["ClaimEvidence"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    findings: Mapped[list["ClaimFinding"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class ClaimEvidence(Base):
    """Join between a claim and all text spans that corroborate it."""

    __tablename__ = "claim_evidence"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True
    )
    span_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("text_spans.id", ondelete="CASCADE"), primary_key=True
    )

    claim: Mapped[Claim] = relationship(back_populates="evidence")
    span: Mapped[TextSpan] = relationship()


class ClaimFinding(Base):
    """Join between a claim and the integrity findings overlapping its evidence."""

    __tablename__ = "claim_findings"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True
    )

    claim: Mapped[Claim] = relationship(back_populates="findings")
    finding: Mapped[Finding] = relationship()


class LLMCall(Identified, Timestamped, Base):
    """Telemetry and cost accounting for an individual call to an LLM provider."""

    __tablename__ = "llm_calls"
    __table_args__ = (Index("ix_llm_calls_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    purpose: Mapped[str] = mapped_column(String(32))
    match_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("match_runs.id", ondelete="SET NULL"), default=None
    )
    job_description_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="SET NULL"), default=None
    )
    model: Mapped[str] = mapped_column(String(64))
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="SET NULL"), default=None
    )
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    latency_ms: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(32))
    stop_reason: Mapped[str | None] = mapped_column(String(32), default=None)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
