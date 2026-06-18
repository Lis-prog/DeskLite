from __future__ import annotations

# Ticket lifecycle state machine.
#
# Single source of truth for *which* status changes are allowed. The status
# values mirror STATUSES in app.models.ticket and TicketStatus in
# app.schemas.ticket; they are duplicated here on purpose, the same dual-guard
# pattern the schemas use (ADR-004): the API/DB validate that a value is a known
# status, and this module validates that a *move* between two statuses is legal.
#
# This module is intentionally free of FastAPI/SQLAlchemy so the rules can be
# unit-tested in isolation and reused by the transition endpoint, audit logging,
# and resolution-time tracking without importing the web/DB layers.

OPEN = "open"
IN_PROGRESS = "in_progress"
RESOLVED = "resolved"
CLOSED = "closed"

STATUSES: tuple[str, ...] = (OPEN, IN_PROGRESS, RESOLVED, CLOSED)

# Directed graph of permitted transitions: a status maps to the set of statuses
# it may move to. Anything not listed here is rejected, including no-op moves to
# the same status.
#
#   open        -> in_progress (agent picks it up), resolved (quick fix),
#                  closed (e.g. spam/duplicate)
#   in_progress -> resolved (work done), open (sent back to the queue),
#                  closed (closed without a formal resolution)
#   resolved    -> closed (confirmed fixed), in_progress (reopened to rework)
#   closed      -> in_progress (reopened)
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    OPEN: frozenset({IN_PROGRESS, RESOLVED, CLOSED}),
    IN_PROGRESS: frozenset({OPEN, RESOLVED, CLOSED}),
    RESOLVED: frozenset({IN_PROGRESS, CLOSED}),
    CLOSED: frozenset({IN_PROGRESS}),
}


class InvalidTransitionError(ValueError):
    """Raised when a requested status change is not permitted.

    Carries the offending ``current``/``target`` statuses so callers (e.g. the
    transition endpoint) can build a precise error response.
    """

    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition ticket from {current!r} to {target!r}.")


def is_valid_status(status: str) -> bool:
    """Return True when ``status`` is one of the known lifecycle states."""
    return status in STATUSES


def allowed_targets(current: str) -> frozenset[str]:
    """Return the set of statuses reachable in one step from ``current``.

    Returns an empty set for an unknown ``current`` status.
    """
    return ALLOWED_TRANSITIONS.get(current, frozenset())


def can_transition(current: str, target: str) -> bool:
    """Return True when moving from ``current`` to ``target`` is allowed.

    Unknown statuses and no-op moves (``current == target``) return False.
    """
    return target in allowed_targets(current)


def validate_transition(current: str, target: str) -> None:
    """Validate a status change, raising on anything illegal.

    Raises:
        InvalidTransitionError: if either status is unknown or the move from
            ``current`` to ``target`` is not in :data:`ALLOWED_TRANSITIONS`.
    """
    if not can_transition(current, target):
        raise InvalidTransitionError(current, target)
