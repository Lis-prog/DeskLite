from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.ticket import TicketPriority, TicketStatus


class TicketMetricsRead(BaseModel):
    """Aggregated ticket counts for dashboard KPIs and charts."""

    total: int = Field(ge=0)
    by_status: dict[TicketStatus, int]
    by_priority: dict[TicketPriority, int]
    unassigned: int = Field(ge=0)


class AgentWorkloadRead(BaseModel):
    """Active ticket load for one support agent."""

    agent_id: int
    full_name: str
    email: str
    active_ticket_count: int = Field(
        ge=0,
        description="Tickets assigned to this agent with status open or in_progress.",
    )
