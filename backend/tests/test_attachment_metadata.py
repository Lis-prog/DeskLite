from __future__ import annotations

from app.models.attachment import Attachment
from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"


def _create_attachment(
    db,
    *,
    ticket_id: int,
    uploader_id: int,
    filename: str = "note.txt",
    content_type: str = "text/plain",
    size: int = 12,
    storage_key: str | None = None,
) -> Attachment:
    attachment = Attachment(
        ticket_id=ticket_id,
        uploader_id=uploader_id,
        filename=filename,
        content_type=content_type,
        size=size,
        storage_key=storage_key or f"tickets/{ticket_id}/{filename}-{uploader_id}",
    )
    db.add(attachment)
    db.flush()
    return attachment


def _list_url(ticket_id: int) -> str:
    return f"{TICKETS_URL}/{ticket_id}/attachments"


# --- Auth -------------------------------------------------------------------


def test_list_attachments_requires_auth(client, db_session):
    customer = create_user(db_session, email="la-noauth@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.get(_list_url(ticket.id))
    assert res.status_code == 401


# --- Happy path -------------------------------------------------------------


def test_owner_lists_ticket_attachments_with_metadata(client, db_session):
    customer = create_user(db_session, email="la-owner@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    first = _create_attachment(
        db_session,
        ticket_id=ticket.id,
        uploader_id=customer.id,
        filename="first.pdf",
        content_type="application/pdf",
        size=2048,
    )
    second = _create_attachment(
        db_session,
        ticket_id=ticket.id,
        uploader_id=customer.id,
        filename="second.txt",
    )

    res = client.get(_list_url(ticket.id), headers=auth_header(customer))

    assert res.status_code == 200
    body = res.json()
    assert [a["id"] for a in body] == [first.id, second.id]

    item = body[0]
    assert item["ticket_id"] == ticket.id
    assert item["uploader_id"] == customer.id
    assert item["filename"] == "first.pdf"
    assert item["content_type"] == "application/pdf"
    assert item["size"] == 2048
    assert "created_at" in item
    assert "storage_key" not in item


def test_list_attachments_empty_when_none(client, db_session):
    customer = create_user(db_session, email="la-empty@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)

    res = client.get(_list_url(ticket.id), headers=auth_header(customer))

    assert res.status_code == 200
    assert res.json() == []


def test_assigned_agent_can_list_attachments(client, db_session):
    agent = create_user(db_session, email="la-agent@test.com", role="agent")
    customer = create_user(db_session, email="la-cust-agent@test.com", role="customer")
    ticket = create_ticket(
        db_session, requester_id=customer.id, assignee_id=agent.id
    )
    _create_attachment(db_session, ticket_id=ticket.id, uploader_id=customer.id)

    res = client.get(_list_url(ticket.id), headers=auth_header(agent))

    assert res.status_code == 200
    assert len(res.json()) == 1


def test_admin_can_list_attachments(client, db_session):
    admin = create_user(db_session, email="la-admin@test.com", role="admin")
    customer = create_user(db_session, email="la-cust-admin@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    _create_attachment(db_session, ticket_id=ticket.id, uploader_id=customer.id)

    res = client.get(_list_url(ticket.id), headers=auth_header(admin))

    assert res.status_code == 200
    assert len(res.json()) == 1


# --- Authorization & isolation ----------------------------------------------


def test_other_customer_cannot_list_attachments(client, db_session):
    owner = create_user(db_session, email="la-owner2@test.com", role="customer")
    other = create_user(db_session, email="la-other@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=owner.id)
    _create_attachment(db_session, ticket_id=ticket.id, uploader_id=owner.id)

    res = client.get(_list_url(ticket.id), headers=auth_header(other))

    assert res.status_code == 403
    assert "filename" not in res.text


def test_unassigned_agent_cannot_list_attachments(client, db_session):
    agent = create_user(db_session, email="la-unassigned@test.com", role="agent")
    customer = create_user(db_session, email="la-cust-un@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    _create_attachment(db_session, ticket_id=ticket.id, uploader_id=customer.id)

    res = client.get(_list_url(ticket.id), headers=auth_header(agent))

    assert res.status_code == 403


def test_list_only_returns_attachments_for_that_ticket(client, db_session):
    customer = create_user(db_session, email="la-scope@test.com", role="customer")
    ticket_a = create_ticket(db_session, requester_id=customer.id, title="A")
    ticket_b = create_ticket(db_session, requester_id=customer.id, title="B")
    on_a = _create_attachment(
        db_session, ticket_id=ticket_a.id, uploader_id=customer.id, filename="a.txt"
    )
    _create_attachment(
        db_session, ticket_id=ticket_b.id, uploader_id=customer.id, filename="b.txt"
    )

    res = client.get(_list_url(ticket_a.id), headers=auth_header(customer))

    assert res.status_code == 200
    body = res.json()
    assert [a["id"] for a in body] == [on_a.id]
    assert body[0]["filename"] == "a.txt"


def test_list_attachments_unknown_ticket_returns_404(client, db_session):
    customer = create_user(db_session, email="la-404@test.com", role="customer")
    res = client.get(_list_url(99999), headers=auth_header(customer))
    assert res.status_code == 404
