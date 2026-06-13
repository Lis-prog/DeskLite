from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.comment import Comment
    from app.models.ticket import Ticket

ROLES = ("customer", "agent", "admin")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="customer")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    
    tickets_raised: Mapped[list[Ticket]] = relationship(  # type: ignore[name-defined]
        "Ticket", foreign_keys="Ticket.requester_id", back_populates="requester"
    )
    tickets_assigned: Mapped[list[Ticket]] = relationship(  # type: ignore[name-defined]
        "Ticket", foreign_keys="Ticket.assignee_id", back_populates="assignee"
    )
    comments: Mapped[list[Comment]] = relationship(  # type: ignore[name-defined]
        "Comment", back_populates="author"
    )
    attachments: Mapped[list[Attachment]] = relationship(  # type: ignore[name-defined]
        "Attachment", back_populates="uploader"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"
