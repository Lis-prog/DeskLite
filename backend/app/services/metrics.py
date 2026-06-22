from __future__ import annotations

from statistics import mean, median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import TicketViewer, scoped_ticket_query
from app.models.ticket import PRIORITIES, STATUSES, Ticket
from app.models.user import User
from app.schemas.metrics import AgentWorkloadRead, ResolutionTimeRead, TicketMetricsRead

_ACTIVE_STATUSES = ("open", "in_progress")


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


def aggregate_agent_workload(db: Session) -> list[AgentWorkloadRead]:
    """Return active ticket counts for every agent, including zero-load agents."""
    agents = list(
        db.scalars(select(User).where(User.role == "agent").order_by(User.full_name, User.id))
    )
    if not agents:
        return []

    counts: dict[int, int] = {
        agent_id: count
        for agent_id, count in db.execute(
            select(Ticket.assignee_id, func.count())
            .where(Ticket.assignee_id.is_not(None))
            .where(Ticket.status.in_(_ACTIVE_STATUSES))
            .group_by(Ticket.assignee_id)
        )
        if agent_id is not None
    }

    return [
        AgentWorkloadRead(
            agent_id=agent.id,
            full_name=agent.full_name,
            email=agent.email,
            active_ticket_count=counts.get(agent.id, 0),
        )
        for agent in agents
    ]


def aggregate_resolution_time(db: Session, user: TicketViewer) -> ResolutionTimeRead:
    """Average and median resolution time over resolved tickets visible to the caller.

    Only tickets carrying a ``resolved_at`` stamp are counted, and the duration is
    measured from ``created_at`` to that first-resolution timestamp. Because
    ``resolved_at`` is never overwritten on re-opens, the numbers stay honest even
    when a ticket bounces back to ``open`` or is resolved again later. Computed in
    Python so the median is portable across databases.
    """
    scoped = scoped_ticket_query(user).order_by(None).subquery()

    rows = db.execute(
        select(scoped.c.created_at, scoped.c.resolved_at).where(
            scoped.c.resolved_at.is_not(None)
        )
    ).all()

    durations = [
        (resolved_at - created_at).total_seconds()
        for created_at, resolved_at in rows
        if created_at is not None and resolved_at is not None
    ]
    # Defensive: ignore any non-positive spans from inconsistent legacy data.
    durations = [seconds for seconds in durations if seconds >= 0]

    if not durations:
        return ResolutionTimeRead(resolved_count=0)

    return ResolutionTimeRead(
        resolved_count=len(durations),
        average_seconds=round(mean(durations), 2),
        median_seconds=round(median(durations), 2),
    )
