from __future__ import annotations

from typing import Protocol

from fastapi import HTTPException, status
from sqlalchemy import Select, select

from app.models.ticket import Ticket


class TicketViewer(Protocol):
    id: int
    role: str


def can_access_ticket(user: TicketViewer, ticket: Ticket) -> bool:
    """Return True when the caller may read or mutate this ticket."""
    if user.role == "admin":
        return True
    if user.role == "agent":
        return ticket.assignee_id == user.id
    if user.role == "customer":
        return ticket.requester_id == user.id
    return False


def ensure_ticket_access(user: TicketViewer, ticket: Ticket) -> None:
    if not can_access_ticket(user, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this ticket.",
        )


def scoped_ticket_query(user: TicketViewer) -> Select[tuple[Ticket]]:
    """Return a SELECT scoped to tickets the caller may list."""
    stmt = select(Ticket).order_by(Ticket.created_at.desc())
    if user.role == "admin":
        return stmt
    if user.role == "agent":
        return stmt.where(Ticket.assignee_id == user.id)
    if user.role == "customer":
        return stmt.where(Ticket.requester_id == user.id)
    return stmt.where(Ticket.id == -1)
