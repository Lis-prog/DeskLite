from __future__ import annotations

from tests.conftest import create_user


def test_register_creates_customer(client, db_session):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@test.com",
            "password": "password123",
            "full_name": "New User",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "new@test.com"
    assert body["role"] == "customer"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_rejects_duplicate_email(client, db_session):
    create_user(db_session, email="dup@test.com")
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@test.com",
            "password": "password123",
            "full_name": "Dup User",
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Email already registered."


def test_register_ignores_role_in_body(client, db_session):
    """Privilege-escalation guard: a client cannot self-assign a role."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "role@test.com",
            "password": "password123",
            "full_name": "Role User",
            "role": "admin",
        },
    )
    assert res.status_code == 201
    assert res.json()["role"] == "customer"


def test_register_rejects_short_password(client, db_session):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "short@test.com",
            "password": "x",
            "full_name": "Short Pass",
        },
    )
    assert res.status_code == 422
