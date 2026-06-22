"""Rate limiting on authentication endpoints (Sprint 3 #66)."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.rate_limit import clear_rate_limits
from tests.conftest import create_user


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    clear_rate_limits()
    yield
    clear_rate_limits()


@pytest.fixture
def strict_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """Tight limits for exercising 429 behaviour in isolation."""
    monkeypatch.setattr(settings, "auth_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "auth_rate_limit_max", 3)
    monkeypatch.setattr(settings, "auth_rate_limit_window_seconds", 60)
    clear_rate_limits()


def test_login_returns_429_after_limit(client, db_session, strict_rate_limit):
    create_user(db_session, email="rl-login@test.com", password="password123")
    payload = {"email": "rl-login@test.com", "password": "wrong"}

    for _ in range(3):
        assert client.post("/api/v1/auth/login", json=payload).status_code == 401

    blocked = client.post("/api/v1/auth/login", json=payload)
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == (
        "Too many authentication attempts. Try again later."
    )
    assert "Retry-After" in blocked.headers


def test_register_returns_429_after_limit(client, db_session, strict_rate_limit):
    for i in range(3):
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"rl-reg-{i}@test.com",
                "password": "password123",
                "full_name": "Rate Limit",
            },
        )
        assert res.status_code == 201

    blocked = client.post(
        "/api/v1/auth/register",
        json={
            "email": "rl-reg-blocked@test.com",
            "password": "password123",
            "full_name": "Blocked",
        },
    )
    assert blocked.status_code == 429


def test_refresh_returns_429_after_limit(client, db_session, strict_rate_limit):
    create_user(db_session, email="rl-refresh@test.com", password="password123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "rl-refresh@test.com", "password": "password123"},
    )
    assert login.status_code == 200

    for _ in range(2):
        assert client.post("/api/v1/auth/refresh").status_code == 200

    blocked = client.post("/api/v1/auth/refresh")
    assert blocked.status_code == 429


def test_rate_limit_disabled_skips_throttle(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "auth_rate_limit_enabled", False)
    monkeypatch.setattr(settings, "auth_rate_limit_max", 1)
    clear_rate_limits()

    for i in range(5):
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"rl-off-{i}@test.com",
                "password": "password123",
                "full_name": "No Limit",
            },
        )
        assert res.status_code == 201
