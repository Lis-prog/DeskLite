from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    """Fields a client may set when posting a comment.

    `author_id` comes from the JWT — never from the body (AGENTS.md §5 rule #1).
    """

    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=10_000)


class CommentAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author_id: int
    author: CommentAuthor
    body: str
    created_at: datetime
