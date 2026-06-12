from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.main import app

client = TestClient(app, raise_server_exceptions=True)


def _make_token(user_id: int, role: str = "customer", email: str = "u@test.com") -> str:
    """Mint a valid access JWT for test use."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode(
        {"sub": str(user_id), "role": role, "email": email, "exp": expire},
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


# IDOR negative-test PATTERN


@pytest.mark.skip(reason="Stub — replace URL + fixture once ticket router exists (DESK-XXX)")
def test_customer_cannot_read_another_users_ticket():
    """
    IDOR guard: customer B requesting ticket owned by customer A gets 403 or 404,
    never the actual data.

    How to activate:
    1. Remove the @pytest.mark.skip decorator.
    2. Create a ticket owned by user_id=1 in the test DB, capture its ticket_id.
    3. Replace /api/v1/tickets/{ticket_id} with the real path.
    """
    ticket_id = 999  # TODO: insert a real ticket owned by user 1

    token = _make_token(user_id=2, role="customer", email="b@test.com")
    res = client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers={"Cookie": f"access_token={token}"},
    )

    assert res.status_code in (403, 404), (
        f"IDOR: user 2 received {res.status_code} on a ticket owned by user 1"
    )
    assert "title" not in res.json()
    