"""Core unit and integration tests for auth, RBAC, and ticket access rules.

Complements ``test_idor.py`` (cross-user by-ID attacks) and ``test_tickets.py``
(happy-path CRUD) by locking down token validation, unknown-role guards, and
remaining mass-assignment edges on ticket updates.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.config import settings
from app.core.dependencies import _UserStub, require_roles
from app.core.permissions import (
    can_access_ticket,
    ensure_ticket_access,
    scoped_ticket_query,
)
from app.core.security import decode_token, verify_password
from app.models.ticket import Ticket
from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"


class _RoleViewer:
    def __init__(self, user_id: int, role: str) -> None:
        self.id = user_id
        self.role = role


def _ticket(*, requester_id: int = 1, assignee_id: int | None = None) -> Ticket:
    return Ticket(
        id=1,
        title="Test ticket",
        description="",
        requester_id=requester_id,
        assignee_id=assignee_id,
    )


# --- permissions (pure unit) ------------------------------------------------


def test_can_access_ticket_unknown_role():
    viewer = _RoleViewer(1, "superuser")
    ticket = _ticket(requester_id=1)
    assert can_access_ticket(viewer, ticket) is False


def test_ensure_ticket_access_raises_for_unknown_role():
    viewer = _RoleViewer(1, "superuser")
    with pytest.raises(HTTPException) as exc:
        ensure_ticket_access(viewer, _ticket(requester_id=1))
    assert exc.value.status_code == 403


def test_scoped_ticket_query_unknown_role_returns_empty(client, db_session):
    admin = create_user(db_session, email="scope-admin@test.com", role="admin")
    customer = create_user(db_session, email="scope-cust@test.com", role="customer")
    create_ticket(db_session, requester_id=customer.id, title="Visible to admin")

    viewer = _RoleViewer(admin.id, "superuser")
    rows = list(db_session.scalars(scoped_ticket_query(viewer)))
    assert rows == []


def test_require_roles_denies_agent_for_admin_only_route():
    check = require_roles("admin")
    agent = _UserStub(id=1, role="agent", email="agent@test.com")
    with pytest.raises(HTTPException) as exc:
        check(user=agent)
    assert exc.value.status_code == 403


# --- security (pure unit) ---------------------------------------------------


def test_verify_password_rejects_malformed_hash():
    assert verify_password("password123", "not-a-bcrypt-hash") is False


def test_decode_token_rejects_wrong_type():
    expire = datetime.now(UTC) + timedelta(hours=1)
    token = jwt.encode(
        {"sub": "1", "role": "customer", "type": "refresh", "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(ValueError, match="Wrong token type"):
        decode_token(token, expected_type="access")


def test_decode_token_rejects_missing_role():
    token = jwt.encode(
        {"sub": "1", "type": "access", "exp": datetime.now(UTC) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(ValueError, match="Missing claims"):
        decode_token(token, expected_type="access")


# --- auth integration -------------------------------------------------------


def test_me_returns_404_when_user_deleted(client, db_session):
    user = create_user(db_session, email="ghost-me@test.com", role="customer")
    headers = auth_header(user)
    db_session.delete(user)
    db_session.flush()

    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "User not found."


def test_refresh_rejects_tampered_token(client):
    res = client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": "refresh_token=not.a.valid.jwt"},
    )
    assert res.status_code == 401


def test_admin_ping_forbidden_for_agent(client, db_session):
    agent = create_user(db_session, email="ping-agent@test.com", role="agent")
    res = client.get("/api/v1/auth/admin/ping", headers=auth_header(agent))
    assert res.status_code == 403


# --- ticket RBAC integration ------------------------------------------------


def test_update_rejects_assignee_id_in_body(client, db_session):
    customer = create_user(db_session, email="upd-assignee@test.com", role="customer")
    agent = create_user(db_session, email="upd-agent@test.com", role="agent")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.patch(
        f"{TICKETS_URL}/{ticket.id}",
        json={"assignee_id": agent.id},
        headers=auth_header(customer),
    )
    assert res.status_code == 422


def test_customer_owner_can_update_description(client, db_session):
    customer = create_user(db_session, email="upd-desc@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        description="Original",
    )
    res = client.patch(
        f"{TICKETS_URL}/{ticket.id}",
        json={"description": "Updated details"},
        headers=auth_header(customer),
    )
    assert res.status_code == 200
    assert res.json()["description"] == "Updated details"


def test_list_tickets_unknown_role_in_token_sees_nothing(client, db_session):
    """JWT role outside the matrix must not widen list scope."""
    user = create_user(db_session, email="bad-role@test.com", role="customer")
    create_ticket(db_session, requester_id=user.id, title="Should not list")

    expire = datetime.now(UTC) + timedelta(minutes=15)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "role": "superuser",
            "email": user.email,
            "type": "access",
            "exp": expire,
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    res = client.get(TICKETS_URL, headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 200
    assert res.json() == []
