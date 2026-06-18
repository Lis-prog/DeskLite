from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.permissions import TicketViewer

if TYPE_CHECKING:
    from app.models.ticket import Ticket


def can_advance_status(user: TicketViewer, ticket: Ticket) -> bool:
    """Only an assigned agent or an admin may change ticket status."""
    if user.role == "admin":
        return True
    if user.role == "agent":
        return ticket.assignee_id == user.id
    return False
