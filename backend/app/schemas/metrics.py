from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.ticket import TicketPriority, TicketStatus


class TicketMetricsRead(BaseModel):
    """Aggregated ticket counts for dashboard KPIs and charts."""

    total: int = Field(ge=0)
    by_status: dict[TicketStatus, int]
    by_priority: dict[TicketPriority, int]
    unassigned: int = Field(ge=0)
