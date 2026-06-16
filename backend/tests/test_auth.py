from __future__ import annotations

from tests.conftest import auth_header, create_user


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


def test_login_valid_credentials_returns_tokens(client, db_session):
    create_user(db_session, email="login@test.com", password="password123")
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "login@test.com", "password": "password123"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    # Tokens are also delivered as httpOnly cookies.
    assert "access_token" in res.cookies
    assert "refresh_token" in res.cookies


def test_login_sets_httponly_cookies(client, db_session):
    create_user(db_session, email="cookie@test.com", password="password123")
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "cookie@test.com", "password": "password123"},
    )
    assert res.status_code == 200
    set_cookie_headers = " ".join(res.headers.get_list("set-cookie")).lower()
    assert "httponly" in set_cookie_headers


def test_login_wrong_password_returns_401(client, db_session):
    create_user(db_session, email="wrongpass@test.com", password="password123")
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@test.com", "password": "not-the-password"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password."


def test_login_unknown_email_returns_401(client, db_session):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@test.com", "password": "password123"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password."


def test_login_unknown_email_and_wrong_password_share_message(client, db_session):
    """Anti user-enumeration: both failure modes return the identical error."""
    create_user(db_session, email="enum@test.com", password="password123")
    wrong_pass = client.post(
        "/api/v1/auth/login",
        json={"email": "enum@test.com", "password": "nope"},
    )
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@test.com", "password": "password123"},
    )
    assert wrong_pass.status_code == unknown.status_code == 401
    assert wrong_pass.json()["detail"] == unknown.json()["detail"]


# --- Logout -----------------------------------------------------------------

def test_logout_requires_auth(client):
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 401


def test_logout_clears_session(client, db_session):
    create_user(db_session, email="logout@test.com", password="password123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "logout@test.com", "password": "password123"},
    )
    assert login.status_code == 200

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    authed = client.get("/api/v1/health/authed")
    assert authed.status_code == 401


# --- Refresh ----------------------------------------------------------------

def test_refresh_requires_refresh_cookie(client):
    res = client.post("/api/v1/auth/refresh")
    assert res.status_code == 401


def test_refresh_renews_access_token(client, db_session):
    create_user(db_session, email="refresh@test.com", password="password123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@test.com", "password": "password123"},
    )
    assert login.status_code == 200

    res = client.post("/api/v1/auth/refresh")
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert "access_token" in res.cookies
    assert "refresh_token" in res.cookies

    authed = client.get("/api/v1/health/authed")
    assert authed.status_code == 200


def test_refresh_rejects_access_token_as_refresh(client, db_session):
    user = create_user(db_session, email="badrefresh@test.com")
    res = client.post("/api/v1/auth/refresh", headers=auth_header(user))
    assert res.status_code == 401


# --- Me ---------------------------------------------------------------------

def test_me_requires_auth(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_me_returns_current_user(client, db_session):
    user = create_user(
        db_session,
        email="me@test.com",
        full_name="Me User",
        role="customer",
    )
    res = client.get("/api/v1/auth/me", headers=auth_header(user))
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == user.id
    assert body["email"] == "me@test.com"
    assert body["full_name"] == "Me User"
    assert body["role"] == "customer"
    assert "password_hash" not in body


# --- Admin ping -------------------------------------------------------------

def test_admin_ping_forbidden_for_customer(client, db_session):
    customer = create_user(db_session, email="ping-cust@test.com", role="customer")
    res = client.get("/api/v1/auth/admin/ping", headers=auth_header(customer))
    assert res.status_code == 403


def test_admin_ping_allowed_for_admin(client, db_session):
    admin = create_user(db_session, email="ping-admin@test.com", role="admin")
    res = client.get("/api/v1/auth/admin/ping", headers=auth_header(admin))
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
