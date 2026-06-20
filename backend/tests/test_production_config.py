from __future__ import annotations

from app.core.config import Settings


def test_s3_presign_endpoint_falls_back_to_internal():
    s = Settings(s3_endpoint="http://minio:9000", s3_public_endpoint="")
    assert s.s3_presign_endpoint == "http://minio:9000"


def test_s3_presign_endpoint_uses_public_when_set():
    s = Settings(
        s3_endpoint="http://minio:9000",
        s3_public_endpoint="https://files.example.com",
    )
    assert s.s3_presign_endpoint == "https://files.example.com"
