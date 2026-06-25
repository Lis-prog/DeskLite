from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.core.config import settings

# Only tickets that still need work can breach their SLA; resolved/closed
# tickets are done and are never flagged as overdue.
ACTIVE_STATUSES = frozenset({"open", "in_progress"})


class _SLATicket(Protocol):
    """Minimal shape needed to evaluate SLA — satisfied by both the ORM
    ``Ticket`` and the ``TicketRead`` schema (duck typing)."""

    status: str
    priority: str
    created_at: datetime


def sla_hours_for(priority: str) -> int:
    """Configured SLA window (in hours) for a ticket priority.

    Falls back to the medium threshold for any unexpected value.
    """
    return {
        "urgent": settings.sla_hours_urgent,
        "high": settings.sla_hours_high,
        "medium": settings.sla_hours_medium,
        "low": settings.sla_hours_low,
    }.get(priority, settings.sla_hours_medium)


def sla_due_at(ticket: _SLATicket) -> datetime:
    """Deadline by which the ticket should be resolved, per its priority SLA."""
    deadline = ticket.created_at + timedelta(hours=sla_hours_for(ticket.priority))
    # Treat naive timestamps as UTC so comparisons never raise.
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return deadline


def is_overdue(ticket: _SLATicket, *, now: datetime | None = None) -> bool:
    """True when an active ticket has passed its SLA deadline."""
    if ticket.status not in ACTIVE_STATUSES:
        return False
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current > sla_due_at(ticket)
