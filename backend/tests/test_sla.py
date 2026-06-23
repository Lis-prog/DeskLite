from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core import sla
from app.core.config import settings
from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"


class _FakeTicket:
    def __init__(self, *, status: str, priority: str, created_at: datetime):
        self.status = status
        self.priority = priority
        self.created_at = created_at


def test_sla_hours_for_uses_configured_thresholds():
    assert sla.sla_hours_for("urgent") == settings.sla_hours_urgent
    assert sla.sla_hours_for("high") == settings.sla_hours_high
    assert sla.sla_hours_for("medium") == settings.sla_hours_medium
    assert sla.sla_hours_for("low") == settings.sla_hours_low
    # Unknown priority falls back to the medium threshold.
    assert sla.sla_hours_for("bogus") == settings.sla_hours_medium


def test_sla_due_at_is_created_plus_threshold():
    created = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    ticket = _FakeTicket(status="open", priority="high", created_at=created)
    assert sla.sla_due_at(ticket) == created + timedelta(hours=settings.sla_hours_high)


def test_active_ticket_past_threshold_is_overdue():
    created = datetime.now(UTC) - timedelta(hours=settings.sla_hours_urgent + 1)
    ticket = _FakeTicket(status="open", priority="urgent", created_at=created)
    assert sla.is_overdue(ticket) is True


def test_recent_active_ticket_is_not_overdue():
    created = datetime.now(UTC) - timedelta(minutes=5)
    ticket = _FakeTicket(status="open", priority="urgent", created_at=created)
    assert sla.is_overdue(ticket) is False


def test_resolved_and_closed_tickets_are_never_overdue():
    old = datetime.now(UTC) - timedelta(days=365)
    for status in ("resolved", "closed"):
        ticket = _FakeTicket(status=status, priority="urgent", created_at=old)
        assert sla.is_overdue(ticket) is False


def test_is_overdue_handles_naive_timestamps():
    naive_old = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
    ticket = _FakeTicket(status="open", priority="low", created_at=naive_old)
    # Must not raise comparing naive vs aware, and an old ticket is overdue.
    assert sla.is_overdue(ticket) is True


def test_ticket_read_exposes_overdue_flag(client, db_session):
    admin = create_user(db_session, email="sla-admin@test.com", role="admin")
    customer = create_user(db_session, email="sla-cust@test.com", role="customer")

    overdue = create_ticket(
        db_session,
        requester_id=customer.id,
        title="Old open ticket",
        status="open",
        priority="urgent",
    )
    overdue.created_at = datetime.now(UTC) - timedelta(days=10)
    fresh = create_ticket(
        db_session,
        requester_id=customer.id,
        title="New open ticket",
        status="open",
        priority="low",
    )
    db_session.flush()

    res = client.get(f"{TICKETS_URL}/{overdue.id}", headers=auth_header(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["is_overdue"] is True
    assert "sla_due_at" in body

    res = client.get(f"{TICKETS_URL}/{fresh.id}", headers=auth_header(admin))
    assert res.status_code == 200
    assert res.json()["is_overdue"] is False
