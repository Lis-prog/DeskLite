from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.core.ticket_state import RESOLVED

if TYPE_CHECKING:
    from app.models.ticket import Ticket


def apply_resolved_at(
    ticket: Ticket,
    new_status: str,
    *,
    now: datetime | None = None,
) -> None:
    """Stamp ``resolved_at`` on the first transition to ``resolved``.

    Re-opens and later re-resolves do not overwrite the original timestamp so
    resolution-time metrics stay honest (first time-to-resolve is preserved).
    """
    if new_status == RESOLVED and ticket.resolved_at is None:
        ticket.resolved_at = now or datetime.now(UTC)


def resolution_duration(ticket: Ticket) -> timedelta | None:
    """Return time from ticket creation to first resolution, if resolved."""
    if ticket.resolved_at is None:
        return None
    return ticket.resolved_at - ticket.created_at
