from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import _UserStub, get_current_user, require_roles
from app.db.session import get_db
from app.schemas.metrics import AgentWorkloadRead, TicketMetricsRead
from app.services.metrics import aggregate_agent_workload, aggregate_ticket_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/tickets", response_model=TicketMetricsRead)
def ticket_metrics(
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> TicketMetricsRead:
    """Return ticket counts grouped by status and priority.

    Counts respect the same role scope as ``GET /api/v1/tickets``.
    """
    return aggregate_ticket_metrics(db, current_user)


@router.get(
    "/agents/workload",
    response_model=list[AgentWorkloadRead],
    dependencies=[Depends(require_roles("admin"))],
)
def agent_workload(db: Session = Depends(get_db)) -> list[AgentWorkloadRead]:
    """Return active ticket counts per agent for workload balancing. Admin-only."""
    return aggregate_agent_workload(db)
