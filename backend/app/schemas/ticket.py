from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Mirror the allowed priority values from the model layer (single source of truth).
Priority = Literal["low", "medium", "high", "urgent"]


class TicketUpdate(BaseModel):
    """Fields a client is allowed to change on an existing ticket.

    Whitelist only. `id`, `requester_id`, `assignee_id`, `status` and timestamps
    are intentionally NOT here: ownership must never change via the client, and
    status moves only through the dedicated transition endpoint (AGENTS.md §5).
    `extra="forbid"` makes any unexpected field a 422 (mass-assignment defense).
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    priority: Priority | None = None


class TicketRead(BaseModel):
    """Shape returned to clients. Never expose the SQLAlchemy model directly."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    priority: str
    requester_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
