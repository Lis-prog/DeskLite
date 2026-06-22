from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    """Metadata returned after a successful upload. Binary content lives in object storage."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    uploader_id: int
    filename: str
    content_type: str
    size: int
    created_at: datetime


class AttachmentDownloadRead(BaseModel):
    """A short-lived presigned download link. The bucket stays private."""

    url: str
    expires_in: int
