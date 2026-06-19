from __future__ import annotations

from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import Select, or_

from app.core.permissions import TicketViewer
from app.models.ticket import Ticket
from app.schemas.ticket import TicketPriority, TicketStatus

TicketListScope = Literal["mine", "all"]


def escape_ilike(term: str) -> str:
    """Escape SQL LIKE/ILIKE wildcards in user-supplied search text."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def validate_list_filters(
    user: TicketViewer,
    *,
    assignee_id: int | None,
    unassigned: bool,
) -> None:
    """Reject filter combinations the caller is not allowed to use."""
    if assignee_id is not None and unassigned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use either assignee_id or unassigned, not both.",
        )
    if (assignee_id is not None or unassigned) and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins may filter by assignee.",
        )


def apply_ticket_list_filters(
    stmt: Select[tuple[Ticket]],
    user: TicketViewer,
    *,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    assignee_id: int | None = None,
    unassigned: bool = False,
    scope: TicketListScope | None = None,
    q: str | None = None,
) -> Select[tuple[Ticket]]:
    """Layer optional filters on top of the role-scoped ticket query."""
    if scope == "mine" and user.role == "admin":
        stmt = stmt.where(
            or_(
                Ticket.assignee_id == user.id,
                Ticket.requester_id == user.id,
            )
        )

    if status is not None:
        stmt = stmt.where(Ticket.status == status)

    if priority is not None:
        stmt = stmt.where(Ticket.priority == priority)

    if unassigned:
        stmt = stmt.where(Ticket.assignee_id.is_(None))
    elif assignee_id is not None:
        stmt = stmt.where(Ticket.assignee_id == assignee_id)

    if q is not None:
        pattern = f"%{escape_ilike(q)}%"
        stmt = stmt.where(
            or_(
                Ticket.title.ilike(pattern, escape="\\"),
                Ticket.description.ilike(pattern, escape="\\"),
            )
        )

    return stmt
