from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

STATUS_CHANGE = "status_change"
ASSIGNMENT_CHANGE = "assignment_change"


def record_status_change(
    db: Session,
    *,
    actor_id: int,
    ticket_id: int,
    from_status: str,
    to_status: str,
) -> AuditLog:
    """Persist who changed a ticket's status and the before/after values."""
    entry = AuditLog(
        actor_id=actor_id,
        ticket_id=ticket_id,
        action=STATUS_CHANGE,
        from_value=from_status,
        to_value=to_status,
    )
    db.add(entry)
    return entry


def record_assignment_change(
    db: Session,
    *,
    actor_id: int,
    ticket_id: int,
    from_assignee_id: int | None,
    to_assignee_id: int | None,
) -> AuditLog:
    """Persist who changed ticket assignment and the before/after assignee ids."""
    entry = AuditLog(
        actor_id=actor_id,
        ticket_id=ticket_id,
        action=ASSIGNMENT_CHANGE,
        from_value=str(from_assignee_id) if from_assignee_id is not None else None,
        to_value=str(to_assignee_id) if to_assignee_id is not None else None,
    )
    db.add(entry)
    return entry
