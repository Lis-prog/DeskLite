"""IDOR regression suite (Sprint 3 #67).

Proves a signed-in user cannot read or mutate another user's ticket (or child
resources) via by-ID routes. Every case must return 403 or 404 and must not
leak the victim's data in the response body.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.storage import StorageService, get_storage_service
from app.main import app
from app.models.attachment import Attachment
from app.models.comment import Comment
from tests.conftest import auth_header, create_ticket, create_user

TICKETS = "/api/v1/tickets"
METRICS_TICKETS = "/api/v1/metrics/tickets"
METRICS_RESOLUTION = "/api/v1/metrics/resolution-time"


@pytest.fixture
def mock_storage(client: TestClient) -> MagicMock:
    storage = MagicMock(spec=StorageService)
    storage.generate_download_url.return_value = "https://minio.local/signed"
    storage.upload.return_value = "tickets/1/key/file.txt"
    app.dependency_overrides[get_storage_service] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage_service, None)


@pytest.fixture
def cross_user_setup(db_session):
    """Victim customer ticket assigned to victim_agent; attacker is another customer."""
    victim = create_user(db_session, email="idor-victim@test.com", role="customer")
    attacker = create_user(db_session, email="idor-attacker@test.com", role="customer")
    victim_agent = create_user(db_session, email="idor-agent@test.com", role="agent")
    ticket = create_ticket(
        db_session,
        requester_id=victim.id,
        assignee_id=victim_agent.id,
        title="Secret victim ticket",
        status="in_progress",
    )
    comment = Comment(
        ticket_id=ticket.id,
        author_id=victim.id,
        body="Private comment",
    )
    db_session.add(comment)
    db_session.flush()

    attachment = Attachment(
        ticket_id=ticket.id,
        uploader_id=victim.id,
        filename="secret.txt",
        content_type="text/plain",
        size=6,
        storage_key=f"tickets/{ticket.id}/abc/secret.txt",
    )
    db_session.add(attachment)
    db_session.flush()

    return {
        "victim": victim,
        "attacker": attacker,
        "agent": victim_agent,
        "ticket": ticket,
        "comment": comment,
        "attachment": attachment,
    }


def _assert_no_leak(body: object, *, secret: str) -> None:
    assert secret not in str(body)


# --- Ticket by ID -----------------------------------------------------------


def test_idor_get_ticket_forbidden(client, cross_user_setup):
    s = cross_user_setup
    res = client.get(
        f"{TICKETS}/{s['ticket'].id}",
        headers=auth_header(s["attacker"]),
    )
    assert res.status_code == 403
    _assert_no_leak(res.json(), secret="Secret victim ticket")


def test_idor_patch_ticket_forbidden(client, cross_user_setup):
    s = cross_user_setup
    res = client.patch(
        f"{TICKETS}/{s['ticket'].id}",
        json={"title": "Hijacked"},
        headers=auth_header(s["attacker"]),
    )
    assert res.status_code == 403
    _assert_no_leak(res.json(), secret="Secret victim ticket")


def test_idor_status_change_forbidden(client, cross_user_setup):
    s = cross_user_setup
    res = client.patch(
        f"{TICKETS}/{s['ticket'].id}/status",
        json={"status": "resolved"},
        headers=auth_header(s["attacker"]),
    )
    assert res.status_code == 403


def test_idor_agent_cannot_access_unassigned_ticket(client, db_session):
    agent = create_user(db_session, email="idor-unassigned-agent@test.com", role="agent")
    customer = create_user(db_session, email="idor-unassigned-cust@test.com", role="customer")
    other_agent = create_user(db_session, email="idor-other-agent@test.com", role="agent")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=other_agent.id,
    )

    res = client.get(f"{TICKETS}/{ticket.id}", headers=auth_header(agent))
    assert res.status_code == 403


# --- Comments ---------------------------------------------------------------


def test_idor_list_comments_forbidden(client, cross_user_setup):
    s = cross_user_setup
    res = client.get(
        f"{TICKETS}/{s['ticket'].id}/comments",
        headers=auth_header(s["attacker"]),
    )
    assert res.status_code == 403
    _assert_no_leak(res.json(), secret="Private comment")


def test_idor_post_comment_forbidden(client, cross_user_setup):
    s = cross_user_setup
    res = client.post(
        f"{TICKETS}/{s['ticket'].id}/comments",
        json={"body": "Intrusion"},
        headers=auth_header(s["attacker"]),
    )
    assert res.status_code == 403


# --- Attachments ------------------------------------------------------------


def test_idor_list_attachments_forbidden(client, cross_user_setup):
    s = cross_user_setup
    res = client.get(
        f"{TICKETS}/{s['ticket'].id}/attachments",
        headers=auth_header(s["attacker"]),
    )
    assert res.status_code == 403
    _assert_no_leak(res.json(), secret="secret.txt")


def test_idor_download_attachment_forbidden(client, cross_user_setup, mock_storage):
    s = cross_user_setup
    res = client.get(
        f"{TICKETS}/{s['ticket'].id}/attachments/{s['attachment'].id}/download",
        headers=auth_header(s["attacker"]),
    )
    assert res.status_code == 403
    mock_storage.generate_download_url.assert_not_called()


def test_idor_upload_attachment_forbidden(client, cross_user_setup, mock_storage):
    s = cross_user_setup
    res = client.post(
        f"{TICKETS}/{s['ticket'].id}/attachments",
        files={"file": ("evil.txt", BytesIO(b"evil"), "text/plain")},
        headers=auth_header(s["attacker"]),
    )
    assert res.status_code == 403
    mock_storage.upload.assert_not_called()


# --- Satisfaction -----------------------------------------------------------


def test_idor_read_satisfaction_forbidden(client, db_session):
    victim = create_user(db_session, email="idor-sat-victim@test.com", role="customer")
    attacker = create_user(db_session, email="idor-sat-attacker@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=victim.id,
        status="closed",
    )

    res = client.get(
        f"{TICKETS}/{ticket.id}/satisfaction",
        headers=auth_header(attacker),
    )
    assert res.status_code == 403


# --- List scope (no row leakage) --------------------------------------------


def test_idor_ticket_list_excludes_other_users_tickets(client, db_session):
    owner = create_user(db_session, email="idor-list-owner@test.com", role="customer")
    other = create_user(db_session, email="idor-list-other@test.com", role="customer")
    mine = create_ticket(db_session, requester_id=owner.id, title="My ticket")
    create_ticket(db_session, requester_id=other.id, title="Their secret ticket")

    res = client.get(TICKETS, headers=auth_header(owner))
    assert res.status_code == 200
    ids = {row["id"] for row in res.json()}
    assert mine.id in ids
    assert all(row["title"] != "Their secret ticket" for row in res.json())


# --- Metrics scope ----------------------------------------------------------


def test_idor_metrics_exclude_other_users_tickets(client, db_session):
    owner = create_user(db_session, email="idor-metrics-owner@test.com", role="customer")
    other = create_user(db_session, email="idor-metrics-other@test.com", role="customer")
    create_ticket(db_session, requester_id=owner.id, status="open")
    create_ticket(db_session, requester_id=other.id, status="open")
    create_ticket(db_session, requester_id=other.id, status="open")

    res = client.get(METRICS_TICKETS, headers=auth_header(owner))
    assert res.status_code == 200
    assert res.json()["total"] == 1


def test_idor_resolution_time_scoped_to_visible_tickets(client, db_session):
    owner = create_user(db_session, email="idor-res-owner@test.com", role="customer")
    other = create_user(db_session, email="idor-res-other@test.com", role="customer")
    base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    mine = create_ticket(db_session, requester_id=owner.id, status="resolved")
    mine.created_at = base
    mine.resolved_at = base + timedelta(hours=1)
    other_ticket = create_ticket(db_session, requester_id=other.id, status="resolved")
    other_ticket.created_at = base
    other_ticket.resolved_at = base + timedelta(hours=2)
    db_session.flush()

    res = client.get(METRICS_RESOLUTION, headers=auth_header(owner))
    assert res.status_code == 200
    assert res.json()["resolved_count"] == 1
