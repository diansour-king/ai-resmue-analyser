import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Identified, Timestamped
from .auth import User


class JobSource(StrEnum):
    PASTED = "pasted"
    UPLOADED = "uploaded"


class JobState(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RequirementKind(StrEnum):
    HARD_SKILL = "hard_skill"
    SOFT_SKILL = "soft_skill"
    EXPERIENCE = "experience"
    CREDENTIAL = "credential"


class RequirementNecessity(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class JobDescription(Identified, Timestamped, Base):
    """A job description submitted by paste or PDF upload."""

    __tablename__ = "job_descriptions"
    __table_args__ = (Index("ix_job_descriptions_user_sha256", "user_id", "sha256", unique=True),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), default=None)
    company: Mapped[str | None] = mapped_column(String(255), default=None)
    location: Mapped[str | None] = mapped_column(String(255), default=None)
    source: Mapped[JobSource] = mapped_column(String(16))
    raw_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str | None] = mapped_column(String(512), default=None)
    page_count: Mapped[int | None] = mapped_column(Integer, default=None)
    state: Mapped[JobState] = mapped_column(String(16), default=JobState.RECEIVED)
    failure_code: Mapped[str | None] = mapped_column(String(32), default=None)
    extractor_version: Mapped[str | None] = mapped_column(String(32), default=None)
    is_fixture: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship()
    requirements: Mapped[list["Requirement"]] = relationship(
        back_populates="job_description", cascade="all, delete-orphan"
    )


class Requirement(Identified, Timestamped, Base):
    """An extracted requirement from a job description with provenance to the source text."""

    __tablename__ = "requirements"
    __table_args__ = (
        Index("ix_requirements_job_ordinal", "job_description_id", "ordinal", unique=True),
    )

    job_description_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    kind: Mapped[RequirementKind] = mapped_column(String(32))
    necessity: Mapped[RequirementNecessity] = mapped_column(String(16))
    criticality: Mapped[int] = mapped_column(Integer)
    weight: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    evidence_start: Mapped[int] = mapped_column(Integer)
    evidence_end: Mapped[int] = mapped_column(Integer)
    evidence_quote: Mapped[str] = mapped_column(Text)
    evidence_page: Mapped[int | None] = mapped_column(Integer, default=None)
    evidence_bbox_x0: Mapped[float | None] = mapped_column(Float, default=None)
    evidence_bbox_y0: Mapped[float | None] = mapped_column(Float, default=None)
    evidence_bbox_x1: Mapped[float | None] = mapped_column(Float, default=None)
    evidence_bbox_y1: Mapped[float | None] = mapped_column(Float, default=None)

    job_description: Mapped[JobDescription] = relationship(back_populates="requirements")
