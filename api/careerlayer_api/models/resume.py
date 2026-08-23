import uuid
from enum import StrEnum

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Identified, Timestamped
from .auth import User


class ProcessingState(StrEnum):
    """The states a resume moves through, and the only ones it may be in.

    Section 6 of the build specification named uploaded/extracting/ready/failed. This is the
    phase 2 replacement: the queue is now visible to the user, so waiting to be picked up and
    actively being worked on are different things worth showing, and "ready" was ambiguous
    about whether analysis had run.
    """

    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FailureCode(StrEnum):
    """A safe classification shown to the user in place of an exception.

    The exception and its traceback go to the log with a resume_id. This is what crosses the
    API boundary, so nothing about the filesystem, the storage layer or the database can leak
    through an error message.
    """

    INVALID_PDF = "invalid_pdf"
    EXTRACTION_FAILED = "extraction_failed"
    RENDER_FAILED = "render_failed"
    OCR_UNAVAILABLE = "ocr_unavailable"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    INTERNAL = "internal"


class Resume(Identified, Timestamped, Base):
    __tablename__ = "resumes"
    __table_args__ = (
        # Re-uploading the same file reuses the analysis instead of paying for it twice.
        Index("ix_resumes_user_sha256", "user_id", "sha256", unique=True),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int | None] = mapped_column(Integer, default=None)
    state: Mapped[ProcessingState] = mapped_column(String(16), default=ProcessingState.UPLOADED)
    failure_code: Mapped[FailureCode | None] = mapped_column(String(32), default=None)

    user: Mapped[User] = relationship()


class ResumePage(Identified, Base):
    """One page, its geometry in PDF points, and where its 200 DPI render lives.

    Both the point geometry and the pixel geometry are stored because the viewer needs both
    to place an overlay: the ratio between them is the scale, and hardcoding it in the
    frontend would break the moment the render DPI changes.
    """

    __tablename__ = "resume_pages"
    __table_args__ = (
        Index("ix_resume_pages_resume_number", "resume_id", "page_number", unique=True),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    width_pt: Mapped[float] = mapped_column(Float)
    height_pt: Mapped[float] = mapped_column(Float)
    rotation: Mapped[int] = mapped_column(Integer, default=0)
    render_key: Mapped[str | None] = mapped_column(String(512), default=None)
    render_width_px: Mapped[int | None] = mapped_column(Integer, default=None)
    render_height_px: Mapped[int | None] = mapped_column(Integer, default=None)
    render_dpi: Mapped[int | None] = mapped_column(Integer, default=None)
    ocr_text: Mapped[str | None] = mapped_column(Text, default=None)


class Extraction(Identified, Timestamped, Base):
    __tablename__ = "extractions"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    method: Mapped[str] = mapped_column(String(16))
    page_count: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)


class TextSpan(Identified, Base):
    """The atomic unit of evidence. Every claim about this document points at one of these."""

    __tablename__ = "text_spans"
    __table_args__ = (Index("ix_text_spans_extraction_page", "extraction_id", "page"),)

    extraction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("extractions.id", ondelete="CASCADE")
    )
    page: Mapped[int] = mapped_column(Integer)
    x0: Mapped[float] = mapped_column(Float)
    y0: Mapped[float] = mapped_column(Float)
    x1: Mapped[float] = mapped_column(Float)
    y1: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    font: Mapped[str] = mapped_column(String(120))
    font_size: Mapped[float] = mapped_column(Float)
    colour: Mapped[str] = mapped_column(String(7))
    render_mode: Mapped[int] = mapped_column(Integer)
    opacity: Mapped[float] = mapped_column(Float)
    seqno: Mapped[int] = mapped_column(Integer)
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)


class Finding(Identified, Timestamped, Base):
    """A persisted integrity finding, with the identity the viewer addresses it by.

    Coordinates are PDF points, exactly as the integrity engine produced them. Nothing here
    is in screen space: the viewer derives the transform from page geometry at render time.
    """

    __tablename__ = "findings"
    __table_args__ = (
        Index("ix_findings_resume_page", "resume_id", "page"),
        CheckConstraint("x1 >= x0 and y1 >= y0", name="ck_findings_bbox_ordered"),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    detector_id: Mapped[str] = mapped_column(String(8))
    detector_name: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    page: Mapped[int] = mapped_column(Integer)
    x0: Mapped[float] = mapped_column(Float)
    y0: Mapped[float] = mapped_column(Float)
    x1: Mapped[float] = mapped_column(Float)
    y1: Mapped[float] = mapped_column(Float)
    excerpt: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)


class ResumeSkill(Identified, Timestamped, Base):
    """A skill read out of the resume, with the evidence that supports it.

    confidence is not an opaque score. It is derived from two counts that are themselves
    stored on this row: how many distinct spans mention the term, and how many of those spans
    an integrity detector flagged. A skill whose only evidence is hidden text is discounted
    and the reason is visible. See careerlayer_api.skills for the formula.
    """

    __tablename__ = "resume_skills"
    __table_args__ = (
        Index("ix_resume_skills_resume_name", "resume_id", "canonical_name", unique=True),
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    canonical_name: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[float] = mapped_column(Float)
    support_count: Mapped[int] = mapped_column(Integer)
    flagged_support_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(32))

    evidence: Mapped[list["SkillEvidence"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )


class SkillEvidence(Base):
    """Join between a skill and the spans that support it.

    A separate table rather than an array column because the whole point is that a reviewer
    can click through to the text, and a foreign key is what makes a dangling reference
    impossible.
    """

    __tablename__ = "skill_evidence"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resume_skills.id", ondelete="CASCADE"), primary_key=True
    )
    span_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("text_spans.id", ondelete="CASCADE"), primary_key=True
    )

    skill: Mapped[ResumeSkill] = relationship(back_populates="evidence")
    span: Mapped[TextSpan] = relationship()
