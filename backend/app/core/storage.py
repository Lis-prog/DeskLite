from __future__ import annotations

import uuid
from pathlib import Path

import boto3
from botocore.config import Config

from app.core.config import settings

# Downloads are served via short-lived presigned URLs so the bucket can stay
# private (AGENTS.md §5, rule #9). Five minutes is enough to start a download
# without leaving a long-lived link in browser history or logs.
DOWNLOAD_URL_EXPIRY_SECONDS = 300


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def build_storage_key(ticket_id: int, filename: str) -> str:
    """Return a unique object key under the ticket prefix."""
    safe_name = Path(filename).name.replace("\\", "_").replace("/", "_")
    unique = uuid.uuid4().hex
    return f"tickets/{ticket_id}/{unique}/{safe_name}"


class StorageService:
    """Upload ticket attachments to MinIO / S3."""

    def __init__(self, client=None) -> None:
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = _s3_client()
        return self._client

    def upload(self, *, key: str, body: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    def generate_download_url(
        self,
        *,
        key: str,
        filename: str,
        expires_in: int = DOWNLOAD_URL_EXPIRY_SECONDS,
    ) -> str:
        """Return a short-lived presigned GET URL for a private object.

        The link expires after `expires_in` seconds and forces a download with
        the original filename. The bucket itself never needs to be public.
        """
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=expires_in,
        )


storage_service = StorageService()


def get_storage_service() -> StorageService:
    return storage_service
