from __future__ import annotations

from fastapi import HTTPException, status

from app.models.ticket import Ticket
from app.models.user import User


def can_access_ticket(user: User, ticket: Ticket) -> bool:
    """Return True when the caller may read or mutate this ticket."""
    if user.role == "admin":
        return True
    if user.role == "agent":
        return ticket.assignee_id == user.id
    if user.role == "customer":
        return ticket.requester_id == user.id
    return False


def ensure_ticket_access(user: User, ticket: Ticket) -> None:
    if not can_access_ticket(user, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this ticket.",
        )
