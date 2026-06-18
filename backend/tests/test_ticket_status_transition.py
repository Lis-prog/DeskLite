from __future__ import annotations

import pytest

from app.core.ticket_state import CLOSED, IN_PROGRESS, OPEN, RESOLVED
from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"

# Mirrors backend/tests/test_ticket_state.py — integration coverage for the endpoint.
VALID_TRANSITIONS = [
    (OPEN, IN_PROGRESS),
    (OPEN, RESOLVED),
    (OPEN, CLOSED),
    (IN_PROGRESS, OPEN),
    (IN_PROGRESS, RESOLVED),
    (IN_PROGRESS, CLOSED),
    (RESOLVED, IN_PROGRESS),
    (RESOLVED, CLOSED),
    (CLOSED, IN_PROGRESS),
]

INVALID_TRANSITIONS = [
    (RESOLVED, OPEN),
    (CLOSED, OPEN),
    (CLOSED, RESOLVED),
    (RESOLVED, RESOLVED),
    (OPEN, OPEN),
    (IN_PROGRESS, IN_PROGRESS),
]


def _status_url(ticket_id: int) -> str:
    return f"{TICKETS_URL}/{ticket_id}/status"


# --- Auth & routing ---------------------------------------------------------


def test_transition_status_requires_auth(client, db_session):
    customer = create_user(db_session, email="st-noauth@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.patch(_status_url(ticket.id), json={"status": "in_progress"})
    assert res.status_code == 401


def test_transition_status_unknown_ticket_returns_404(client, db_session):
    admin = create_user(db_session, email="st-404@test.com", role="admin")
    res = client.patch(
        _status_url(99999),
        json={"status": "in_progress"},
        headers=auth_header(admin),
    )
    assert res.status_code == 404


# --- Role rules -------------------------------------------------------------


def test_admin_can_advance_status(client, db_session):
    admin = create_user(db_session, email="st-admin@test.com", role="admin")
    customer = create_user(db_session, email="st-cust-admin@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id, status="open")

    res = client.patch(
        _status_url(ticket.id),
        json={"status": "in_progress"},
        headers=auth_header(admin),
    )

    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"


def test_assigned_agent_can_advance_status(client, db_session):
    agent = create_user(db_session, email="st-agent@test.com", role="agent")
    customer = create_user(db_session, email="st-cust-agent@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=agent.id,
        status="open",
    )

    res = client.patch(
        _status_url(ticket.id),
        json={"status": "in_progress"},
        headers=auth_header(agent),
    )

    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"


def test_customer_cannot_advance_own_ticket_status(client, db_session):
    customer = create_user(db_session, email="st-cust-deny@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id, status="open")

    res = client.patch(
        _status_url(ticket.id),
        json={"status": "in_progress"},
        headers=auth_header(customer),
    )

    assert res.status_code == 403
    assert res.json()["detail"] == (
        "Only the assigned agent or an admin can change ticket status."
    )


def test_unassigned_agent_cannot_advance_status(client, db_session):
    agent = create_user(db_session, email="st-unassigned@test.com", role="agent")
    customer = create_user(db_session, email="st-cust-unassigned@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id, status="open")

    res = client.patch(
        _status_url(ticket.id),
        json={"status": "in_progress"},
        headers=auth_header(agent),
    )

    assert res.status_code == 403


def test_other_assigned_agent_cannot_advance_status(client, db_session):
    assigned = create_user(db_session, email="st-assigned@test.com", role="agent")
    other_agent = create_user(db_session, email="st-other-agent@test.com", role="agent")
    customer = create_user(db_session, email="st-cust-other@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=assigned.id,
        status="open",
    )

    res = client.patch(
        _status_url(ticket.id),
        json={"status": "in_progress"},
        headers=auth_header(other_agent),
    )

    assert res.status_code == 403


# --- State machine ----------------------------------------------------------


@pytest.mark.parametrize(("current", "new"), VALID_TRANSITIONS)
def test_valid_status_transitions(client, db_session, current, new):
    admin = create_user(db_session, email=f"st-{current}-{new}@test.com", role="admin")
    customer = create_user(
        db_session,
        email=f"st-cust-{current}-{new}@test.com",
        role="customer",
    )
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        status=current,
    )

    res = client.patch(
        _status_url(ticket.id),
        json={"status": new},
        headers=auth_header(admin),
    )

    assert res.status_code == 200
    assert res.json()["status"] == new


@pytest.mark.parametrize(("current", "new"), INVALID_TRANSITIONS)
def test_invalid_status_transitions_return_400(client, db_session, current, new):
    admin = create_user(db_session, email=f"st-bad-{current}-{new}@test.com", role="admin")
    customer = create_user(
        db_session,
        email=f"st-cust-bad-{current}-{new}@test.com",
        role="customer",
    )
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        status=current,
    )

    res = client.patch(
        _status_url(ticket.id),
        json={"status": new},
        headers=auth_header(admin),
    )

    assert res.status_code == 400
    assert "Cannot transition ticket" in res.json()["detail"]
