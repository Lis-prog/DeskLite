from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Mirror the DB CHECK constraints (see models/ticket.py). Dual-guard per ADR-004:
# invalid values are rejected here (422) and again by the database.
TicketStatus = Literal["open", "in_progress", "resolved", "closed"]
TicketPriority = Literal["low", "medium", "high", "urgent"]


class TicketCreate(BaseModel):
    """Fields a client may set when opening a ticket.

    Whitelist only. `requester_id` comes from the JWT, `status` starts as
    "open" server-side, and `assignee_id`/timestamps are never client-set —
    so they are intentionally absent here. `extra="forbid"` makes any attempt
    to send them fail with 422 rather than being silently ignored.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20_000)
    priority: TicketPriority = "medium"


class TicketUpdate(BaseModel):
    """Editable fields on an existing ticket.

    Excludes `status` (changed only via the dedicated transition payload),
    plus `assignee_id`, `requester_id` and timestamps. All fields optional so
    a partial update sends only what changes.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    priority: TicketPriority | None = None


class TicketStatusUpdate(BaseModel):
    """Dedicated status-transition payload. Kept separate so a client can never
    flip status through the generic update path (AGENTS.md §5, rule #2)."""

    model_config = ConfigDict(extra="forbid")

    status: TicketStatus


class TicketRead(BaseModel):
    """Full read shape returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    requester_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
