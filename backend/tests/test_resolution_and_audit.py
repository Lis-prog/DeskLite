from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.resolution_tracking import apply_resolved_at, resolution_duration
from app.core.ticket_state import CLOSED, IN_PROGRESS, RESOLVED
from app.models.audit_log import AuditLog
from app.models.ticket import Ticket
from app.services.audit import ASSIGNMENT_CHANGE, STATUS_CHANGE
from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"
ADMIN_ASSIGN_URL = "/api/v1/admin/tickets/{ticket_id}/assignee"
FIXED_NOW = datetime(2026, 6, 18, 12, 0, tzinfo=UTC)


def _status_url(ticket_id: int) -> str:
    return f"{TICKETS_URL}/{ticket_id}/status"


def _audit_logs(db, ticket_id: int, action: str) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.ticket_id == ticket_id, AuditLog.action == action)
            .order_by(AuditLog.id)
        )
    )


# --- resolution_tracking unit tests -------------------------------------------


def test_apply_resolved_at_sets_timestamp_on_first_resolve():
    ticket = Ticket(
        title="t",
        description="",
        status=IN_PROGRESS,
        requester_id=1,
        created_at=FIXED_NOW - timedelta(hours=2),
    )
    apply_resolved_at(ticket, RESOLVED, now=FIXED_NOW)
    assert ticket.resolved_at == FIXED_NOW


def test_apply_resolved_at_does_not_overwrite_existing_timestamp():
    first = FIXED_NOW - timedelta(days=1)
    ticket = Ticket(
        title="t",
        description="",
        status=IN_PROGRESS,
        requester_id=1,
        created_at=FIXED_NOW - timedelta(days=2),
        resolved_at=first,
    )
    apply_resolved_at(ticket, RESOLVED, now=FIXED_NOW)
    assert ticket.resolved_at == first


def test_apply_resolved_at_ignores_non_resolved_status():
    ticket = Ticket(
        title="t",
        description="",
        status=IN_PROGRESS,
        requester_id=1,
        created_at=FIXED_NOW,
    )
    apply_resolved_at(ticket, IN_PROGRESS, now=FIXED_NOW)
    assert ticket.resolved_at is None


def test_apply_resolved_at_backfills_on_close_from_resolved():
    ticket = Ticket(
        title="t",
        description="",
        status=RESOLVED,
        requester_id=1,
        created_at=FIXED_NOW - timedelta(days=2),
    )
    apply_resolved_at(
        ticket,
        CLOSED,
        from_status=RESOLVED,
        now=FIXED_NOW,
    )
    assert ticket.resolved_at == FIXED_NOW


def test_resolution_duration_returns_elapsed_time():
    created = FIXED_NOW - timedelta(hours=3)
    ticket = Ticket(
        title="t",
        description="",
        status=RESOLVED,
        requester_id=1,
        created_at=created,
        resolved_at=FIXED_NOW,
    )
    assert resolution_duration(ticket) == timedelta(hours=3)


def test_resolution_duration_none_when_unresolved():
    ticket = Ticket(
        title="t",
        description="",
        status=IN_PROGRESS,
        requester_id=1,
        created_at=FIXED_NOW,
    )
    assert resolution_duration(ticket) is None


# --- #37 integration: resolved_at on status transition ------------------------


def test_transition_to_resolved_sets_resolved_at(client, db_session):
    admin = create_user(db_session, email="res-admin@test.com", role="admin")
    customer = create_user(db_session, email="res-cust@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        status=IN_PROGRESS,
    )

    res = client.patch(
        _status_url(ticket.id),
        json={"status": "resolved"},
        headers=auth_header(admin),
    )

    assert res.status_code == 200
    assert res.json()["resolved_at"] is not None


def test_reopen_preserves_first_resolved_at(client, db_session):
    admin = create_user(db_session, email="res-reopen@test.com", role="admin")
    customer = create_user(db_session, email="res-reopen-cust@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        status=IN_PROGRESS,
    )

    first = client.patch(
        _status_url(ticket.id),
        json={"status": "resolved"},
        headers=auth_header(admin),
    )
    first_resolved_at = first.json()["resolved_at"]

    client.patch(
        _status_url(ticket.id),
        json={"status": "in_progress"},
        headers=auth_header(admin),
    )
    second = client.patch(
        _status_url(ticket.id),
        json={"status": "resolved"},
        headers=auth_header(admin),
    )

    assert second.json()["resolved_at"] == first_resolved_at


def test_open_to_resolved_sets_resolved_at(client, db_session):
    admin = create_user(db_session, email="res-skip@test.com", role="admin")
    customer = create_user(db_session, email="res-skip-cust@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id, status="open")

    res = client.patch(
        _status_url(ticket.id),
        json={"status": "resolved"},
        headers=auth_header(admin),
    )

    assert res.status_code == 200
    assert res.json()["resolved_at"] is not None


# --- #38 integration: audit log on status / assignment ------------------------


@pytest.mark.parametrize(
    ("current", "new"),
    [("open", "in_progress"), ("in_progress", "resolved")],
)
def test_status_transition_writes_audit_log(client, db_session, current, new):
    admin = create_user(
        db_session,
        email=f"audit-st-{current}-{new}@test.com",
        role="admin",
    )
    customer = create_user(
        db_session,
        email=f"audit-st-cust-{current}-{new}@test.com",
        role="customer",
    )
    ticket = create_ticket(db_session, requester_id=customer.id, status=current)

    res = client.patch(
        _status_url(ticket.id),
        json={"status": new},
        headers=auth_header(admin),
    )
    assert res.status_code == 200

    logs = _audit_logs(db_session, ticket.id, STATUS_CHANGE)
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].from_value == current
    assert logs[0].to_value == new


def test_assignment_writes_audit_log(client, db_session):
    admin = create_user(db_session, email="audit-asgn-admin@test.com", role="admin")
    agent = create_user(db_session, email="audit-asgn-agent@test.com", role="agent")
    customer = create_user(db_session, email="audit-asgn-cust@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)

    res = client.patch(
        ADMIN_ASSIGN_URL.format(ticket_id=ticket.id),
        json={"assignee_id": agent.id},
        headers=auth_header(admin),
    )
    assert res.status_code == 200

    logs = _audit_logs(db_session, ticket.id, ASSIGNMENT_CHANGE)
    assert len(logs) == 1
    assert logs[0].actor_id == admin.id
    assert logs[0].from_value is None
    assert logs[0].to_value == str(agent.id)


def test_unassign_writes_audit_log_with_null_to_value(client, db_session):
    admin = create_user(db_session, email="audit-unadmin@test.com", role="admin")
    agent = create_user(db_session, email="audit-unagent@test.com", role="agent")
    customer = create_user(db_session, email="audit-uncust@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=agent.id,
    )

    res = client.patch(
        ADMIN_ASSIGN_URL.format(ticket_id=ticket.id),
        json={"assignee_id": None},
        headers=auth_header(admin),
    )
    assert res.status_code == 200

    logs = _audit_logs(db_session, ticket.id, ASSIGNMENT_CHANGE)
    assert len(logs) == 1
    assert logs[0].from_value == str(agent.id)
    assert logs[0].to_value is None
