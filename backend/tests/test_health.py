from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.dependencies import _UserStub, require_roles
from app.db.session import get_db
from app.main import app

client = TestClient(app, raise_server_exceptions=True)


def _make_token(user_id: int, role: str = "customer", email: str = "u@test.com") -> str:
    """Mint a valid access JWT for test use."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode(
    {
        "sub": str(user_id),
        "role": role,
        "email": email,
        "type": "access",
        "exp": expire,
    },
    settings.jwt_secret,
    algorithm=settings.jwt_algorithm,
)

# root

def test_health_ok():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "desklite-backend"


def test_health_db_ok():
    res = client.get("/api/v1/health/db")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"


def test_health_db_unavailable_returns_503():
    """When Postgres is unreachable, readiness must surface a 503 so monitors
    and orchestrators detect downtime from the status code."""

    class _BoomSession:
        def execute(self, *args, **kwargs):
            raise RuntimeError("database unavailable")

    def _override_get_db():
        yield _BoomSession()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        res = client.get("/api/v1/health/db")
        assert res.status_code == 503
        body = res.json()
        assert body["status"] == "degraded"
        assert body["database"] == "unavailable"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_root_ok():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["name"] == "DeskLite API"

# Auth dependency tests

def test_health_authed_no_cookie_returns_401():
    """No JWT cookie → must get 401, never 200."""
    res = client.get("/api/v1/health/authed")
    assert res.status_code == 401


def test_health_authed_invalid_token_returns_401():
    """Tampered token → 401."""
    res = client.get(
        "/api/v1/health/authed",
        headers={"Cookie": "access_token=not.a.real.token"},
    )
    assert res.status_code == 401


def test_health_authed_refresh_token_returns_401():
    """Refresh token used on protected route → 401."""
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_days)
    token = jwt.encode(
        {
            "sub": "42",
            "role": "agent",
            "email": "agent@test.com",
            "type": "refresh",
            "exp": expire,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    res = client.get(
        "/api/v1/health/authed",
        headers={"Cookie": f"access_token={token}"},
    )

    assert res.status_code == 401


def test_health_authed_valid_token_returns_caller_identity():
    """Valid JWT → returns the correct user_id and role from the token."""
    token = _make_token(user_id=42, role="agent")
    res = client.get(
        "/api/v1/health/authed",
        headers={"Cookie": f"access_token={token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == 42
    assert body["role"] == "agent"


def test_require_roles_allows_matching_role():
    check = require_roles("admin")
    user = _UserStub(id=1, role="admin", email="a@test.com")
    assert check(user=user) is user


def test_require_roles_denies_wrong_role():
    check = require_roles("admin")
    user = _UserStub(id=1, role="customer", email="a@test.com")
    with pytest.raises(HTTPException) as exc:
        check(user=user)
    assert exc.value.status_code == 403