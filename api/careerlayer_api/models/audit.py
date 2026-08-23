import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, Identified, Timestamped


class AuditLog(Identified, Timestamped, Base):
    """An immutable audit trail of security-relevant and state-changing events."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    action: Mapped[str] = mapped_column(String(64))
    subject_type: Mapped[str] = mapped_column(String(64))
    subject_id: Mapped[str] = mapped_column(String(64))
