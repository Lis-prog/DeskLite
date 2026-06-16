from __future__ import annotations

from tests.conftest import auth_header, create_user

USERS_URL = "/api/v1/admin/users"


# --- RBAC on the admin user listing -------------------------------------

def test_list_users_requires_auth(client):
    """No token → 401, never the data."""
    res = client.get(USERS_URL)
    assert res.status_code == 401


def test_list_users_forbidden_for_customer(client, db_session):
    customer = create_user(db_session, email="cust@test.com", role="customer")
    res = client.get(USERS_URL, headers=auth_header(customer))
    assert res.status_code == 403


def test_list_users_forbidden_for_agent(client, db_session):
    agent = create_user(db_session, email="agent@test.com", role="agent")
    res = client.get(USERS_URL, headers=auth_header(agent))
    assert res.status_code == 403


def test_list_users_allowed_for_admin(client, db_session):
    admin = create_user(db_session, email="admin@test.com", role="admin")
    create_user(db_session, email="someone@test.com", role="customer")

    res = client.get(USERS_URL, headers=auth_header(admin))
    assert res.status_code == 200

    body = res.json()
    emails = {u["email"] for u in body}
    assert {"admin@test.com", "someone@test.com"} <= emails
    # never leak the password hash
    assert all("password_hash" not in u for u in body)


# --- RBAC + behavior on role assignment ---------------------------------

def test_assign_role_requires_auth(client, db_session):
    target = create_user(db_session, email="t@test.com", role="customer")
    res = client.patch(f"{USERS_URL}/{target.id}/role", json={"role": "agent"})
    assert res.status_code == 401


def test_assign_role_forbidden_for_non_admin(client, db_session):
    actor = create_user(db_session, email="actor@test.com", role="agent")
    target = create_user(db_session, email="t2@test.com", role="customer")
    res = client.patch(
        f"{USERS_URL}/{target.id}/role",
        json={"role": "agent"},
        headers=auth_header(actor),
    )
    assert res.status_code == 403


def test_admin_can_assign_role(client, db_session):
    admin = create_user(db_session, email="boss@test.com", role="admin")
    target = create_user(db_session, email="promote@test.com", role="customer")

    res = client.patch(
        f"{USERS_URL}/{target.id}/role",
        json={"role": "agent"},
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    assert res.json()["role"] == "agent"


def test_assign_invalid_role_rejected(client, db_session):
    admin = create_user(db_session, email="boss2@test.com", role="admin")
    target = create_user(db_session, email="t3@test.com", role="customer")
    res = client.patch(
        f"{USERS_URL}/{target.id}/role",
        json={"role": "superuser"},
        headers=auth_header(admin),
    )
    assert res.status_code == 422


def test_assign_role_unknown_user_returns_404(client, db_session):
    admin = create_user(db_session, email="boss3@test.com", role="admin")
    res = client.patch(
        f"{USERS_URL}/999999/role",
        json={"role": "agent"},
        headers=auth_header(admin),
    )
    assert res.status_code == 404
