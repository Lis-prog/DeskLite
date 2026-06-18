from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.core.ticket_state import CLOSED, RESOLVED

if TYPE_CHECKING:
    from app.models.ticket import Ticket


def apply_resolved_at(
    ticket: Ticket,
    new_status: str,
    *,
    from_status: str | None = None,
    now: datetime | None = None,
) -> None:
    """Stamp ``resolved_at`` on the first transition to ``resolved``.

    Also backfills when closing a ticket that was already ``resolved`` but never
    stamped (e.g. legacy seed rows). Re-opens and later re-resolves do not
    overwrite the original timestamp so resolution-time metrics stay honest.
    """
    if ticket.resolved_at is not None:
        return
    stamp = now or datetime.now(UTC)
    if new_status == RESOLVED:
        ticket.resolved_at = stamp
    elif new_status == CLOSED and from_status == RESOLVED:
        ticket.resolved_at = stamp


def resolution_duration(ticket: Ticket) -> timedelta | None:
    """Return time from ticket creation to first resolution, if resolved."""
    if ticket.resolved_at is None:
        return None
    return ticket.resolved_at - ticket.created_at
