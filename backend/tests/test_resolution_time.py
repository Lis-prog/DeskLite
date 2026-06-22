from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.ticket import Ticket
from tests.conftest import auth_header, create_ticket, create_user

RESOLUTION_URL = "/api/v1/metrics/resolution-time"

_BASE = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)


def _resolve(db, ticket: Ticket, *, hours: float, status: str = "resolved") -> None:
    """Pin a deterministic created->resolved span on an existing ticket."""
    ticket.created_at = _BASE
    ticket.resolved_at = _BASE + timedelta(hours=hours)
    ticket.status = status
    db.flush()


def test_resolution_time_requires_authentication(client):
    res = client.get(RESOLUTION_URL)
    assert res.status_code == 401


def test_no_resolved_tickets_returns_nulls(client, db_session):
    admin = create_user(db_session, email="res-empty-admin@test.com", role="admin")
    customer = create_user(db_session, email="res-empty-cust@test.com", role="customer")
    create_ticket(db_session, requester_id=customer.id, title="Still open", status="open")

    res = client.get(RESOLUTION_URL, headers=auth_header(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["resolved_count"] == 0
    assert body["average_seconds"] is None
    assert body["median_seconds"] is None


def test_admin_average_and_median_over_resolved_tickets(client, db_session):
    admin = create_user(db_session, email="res-admin@test.com", role="admin")
    customer = create_user(db_session, email="res-cust@test.com", role="customer")

    # Durations of 1h, 2h, 6h -> mean 3h (10800s), median 2h (7200s).
    for hours in (1, 2, 6):
        ticket = create_ticket(
            db_session,
            requester_id=customer.id,
            title=f"Resolved in {hours}h",
            status="resolved",
        )
        _resolve(db_session, ticket, hours=hours)

    res = client.get(RESOLUTION_URL, headers=auth_header(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["resolved_count"] == 3
    assert body["average_seconds"] == 10800.0
    assert body["median_seconds"] == 7200.0


def test_open_tickets_are_excluded(client, db_session):
    admin = create_user(db_session, email="res-mixed-admin@test.com", role="admin")
    customer = create_user(db_session, email="res-mixed-cust@test.com", role="customer")

    resolved = create_ticket(
        db_session, requester_id=customer.id, title="Resolved", status="resolved"
    )
    _resolve(db_session, resolved, hours=2)
    create_ticket(db_session, requester_id=customer.id, title="Open", status="open")
    create_ticket(
        db_session, requester_id=customer.id, title="In progress", status="in_progress"
    )

    res = client.get(RESOLUTION_URL, headers=auth_header(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["resolved_count"] == 1
    assert body["average_seconds"] == 7200.0
    assert body["median_seconds"] == 7200.0


def test_reopened_ticket_keeps_original_resolution_time(client, db_session):
    """A ticket resolved once then re-opened must still count, using its first
    (original) resolution timestamp -- re-opens are handled honestly."""
    admin = create_user(db_session, email="res-reopen-admin@test.com", role="admin")
    customer = create_user(db_session, email="res-reopen-cust@test.com", role="customer")

    # resolved_at stamped at +3h on first resolution; ticket later bounced to open.
    reopened = create_ticket(
        db_session, requester_id=customer.id, title="Reopened", status="open"
    )
    _resolve(db_session, reopened, hours=3, status="open")

    res = client.get(RESOLUTION_URL, headers=auth_header(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["resolved_count"] == 1
    assert body["average_seconds"] == 10800.0
    assert body["median_seconds"] == 10800.0


def test_customer_only_sees_own_resolution_time(client, db_session):
    customer = create_user(db_session, email="res-own-cust@test.com", role="customer")
    other = create_user(db_session, email="res-other-cust@test.com", role="customer")

    mine = create_ticket(
        db_session, requester_id=customer.id, title="Mine", status="resolved"
    )
    _resolve(db_session, mine, hours=1)
    theirs = create_ticket(
        db_session, requester_id=other.id, title="Theirs", status="resolved"
    )
    _resolve(db_session, theirs, hours=10)

    res = client.get(RESOLUTION_URL, headers=auth_header(customer))
    assert res.status_code == 200
    body = res.json()
    assert body["resolved_count"] == 1
    assert body["average_seconds"] == 3600.0
    assert body["median_seconds"] == 3600.0
