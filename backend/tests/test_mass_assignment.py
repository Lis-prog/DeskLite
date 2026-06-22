"""Mass-assignment / input-validation review for the user & auth surfaces.

Outcome under review: *no client can set protected fields like role or
ownership*. Ticket ownership/status are already covered in ``test_tickets.py``;
this module locks in the auth/user schemas, which now forbid unexpected fields
so privilege-escalation attempts fail with 422 instead of being silently
ignored.
"""

from __future__ import annotations

from tests.conftest import auth_header, create_user

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ROLE_URL = "/api/v1/admin/users/{user_id}/role"


# --- Registration: protected/unknown fields are rejected -------------------

def test_register_rejects_role_field(client, db_session):
    res = client.post(
        REGISTER_URL,
        json={
            "email": "ma-role@test.com",
            "password": "password123",
            "full_name": "Mallory",
            "role": "admin",
        },
    )
    assert res.status_code == 422


def test_register_rejects_unknown_privilege_field(client, db_session):
    res = client.post(
        REGISTER_URL,
        json={
            "email": "ma-isadmin@test.com",
            "password": "password123",
            "full_name": "Mallory",
            "is_admin": True,
        },
    )
    assert res.status_code == 422


def test_register_rejects_id_injection(client, db_session):
    res = client.post(
        REGISTER_URL,
        json={
            "email": "ma-id@test.com",
            "password": "password123",
            "full_name": "Mallory",
            "id": 1,
        },
    )
    assert res.status_code == 422


def test_register_clean_payload_still_succeeds(client, db_session):
    """The hardening must not break the legitimate, whitelisted payload."""
    res = client.post(
        REGISTER_URL,
        json={
            "email": "ma-ok@test.com",
            "password": "password123",
            "full_name": "Honest User",
        },
    )
    assert res.status_code == 201
    assert res.json()["role"] == "customer"


# --- Login: unexpected fields are rejected ---------------------------------

def test_login_rejects_unknown_field(client, db_session):
    create_user(db_session, email="ma-login@test.com", password="password123")
    res = client.post(
        LOGIN_URL,
        json={
            "email": "ma-login@test.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert res.status_code == 422


# --- Role update: only `role` is accepted ----------------------------------

def test_role_update_rejects_extra_field(client, db_session):
    admin = create_user(db_session, email="ma-admin@test.com", role="admin")
    target = create_user(db_session, email="ma-target@test.com", role="customer")
    res = client.patch(
        ROLE_URL.format(user_id=target.id),
        json={"role": "agent", "email": "hacked@test.com"},
        headers=auth_header(admin),
    )
    assert res.status_code == 422
