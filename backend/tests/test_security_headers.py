from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.security_headers import build_security_headers
from app.main import app

client = TestClient(app, raise_server_exceptions=True)


def test_build_security_headers_omits_hsts_by_default():
    headers = build_security_headers(enable_hsts=False)
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" not in headers


def test_build_security_headers_includes_hsts_in_production():
    headers = build_security_headers(enable_hsts=True)
    assert headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_api_responses_include_security_headers():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Strict-Transport-Security" not in res.headers
