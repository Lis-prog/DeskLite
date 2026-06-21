from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import TicketViewer, scoped_ticket_query
from app.models.ticket import PRIORITIES, STATUSES
from app.schemas.metrics import TicketMetricsRead


def _empty_counts() -> tuple[dict[str, int], dict[str, int]]:
    return (
        {status: 0 for status in STATUSES},
        {priority: 0 for priority in PRIORITIES},
    )


def aggregate_ticket_metrics(db: Session, user: TicketViewer) -> TicketMetricsRead:
    """Count tickets visible to the caller, grouped by status and priority."""
    scoped = scoped_ticket_query(user).order_by(None).subquery()

    total = db.scalar(select(func.count()).select_from(scoped)) or 0
    by_status, by_priority = _empty_counts()

    for status, count in db.execute(
        select(scoped.c.status, func.count()).group_by(scoped.c.status)
    ):
        if status in by_status:
            by_status[status] = count

    for priority, count in db.execute(
        select(scoped.c.priority, func.count()).group_by(scoped.c.priority)
    ):
        if priority in by_priority:
            by_priority[priority] = count

    unassigned = (
        db.scalar(
            select(func.count())
            .select_from(scoped)
            .where(scoped.c.assignee_id.is_(None))
        )
        or 0
    )

    return TicketMetricsRead(
        total=total,
        by_status=by_status,  # type: ignore[arg-type]
        by_priority=by_priority,  # type: ignore[arg-type]
        unassigned=unassigned,
    )
