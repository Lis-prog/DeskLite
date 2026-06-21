from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.audit_log import AuditLog
    from app.models.comment import Comment
    from app.models.user import User

STATUSES = ("open", "in_progress", "resolved", "closed")
PRIORITIES = ("low", "medium", "high", "urgent")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", index=True
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium", index=True
    )

    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    requester: Mapped[User] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[requester_id], back_populates="tickets_raised"
    )
    assignee: Mapped[User | None] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[assignee_id], back_populates="tickets_assigned"
    )
    comments: Mapped[list[Comment]] = relationship(  # type: ignore[name-defined]
        "Comment", back_populates="ticket", cascade="all, delete-orphan"
    )
    attachments: Mapped[list[Attachment]] = relationship(  # type: ignore[name-defined]
        "Attachment", back_populates="ticket", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(  # type: ignore[name-defined]
        "AuditLog", back_populates="ticket", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} status={self.status!r} priority={self.priority!r}>"
