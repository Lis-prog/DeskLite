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


class ResolutionTimeRead(BaseModel):
    """Average and median resolution time over resolved tickets.

    Durations are measured from ticket creation to the first time it was
    resolved, so re-opens never overwrite the timestamp or inflate the numbers.
    """

    resolved_count: int = Field(
        ge=0,
        description="Tickets with a recorded first-resolution timestamp.",
    )
    average_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Mean creation-to-resolution time in seconds; null when none resolved.",
    )
    median_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Median creation-to-resolution time in seconds; null when none resolved.",
    )
