from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.sanitize import sanitize_user_text


class CommentCreate(BaseModel):
    """Fields a client may set when posting a comment.

    `author_id` comes from the JWT — never from the body (permission-matrix, golden rule #1).
    Comment text is stripped of HTML markup to prevent stored XSS (§5 rule #7).
    """

    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=10_000)

    @field_validator("body")
    @classmethod
    def _sanitize_body(cls, value: str) -> str:
        cleaned = sanitize_user_text(value)
        if not cleaned:
            raise ValueError("Comment body cannot be empty.")
        return cleaned


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
