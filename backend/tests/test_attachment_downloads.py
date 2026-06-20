from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.storage import (
    DOWNLOAD_URL_EXPIRY_SECONDS,
    StorageService,
    get_storage_service,
)
from app.main import app
from app.models.attachment import Attachment
from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"
SIGNED_URL = "https://minio.local/desklite-attachments/signed?X-Amz-Expires=300"


def _create_attachment(
    db,
    *,
    ticket_id: int,
    uploader_id: int,
    filename: str = "note.txt",
    content_type: str = "text/plain",
    storage_key: str | None = None,
) -> Attachment:
    attachment = Attachment(
        ticket_id=ticket_id,
        uploader_id=uploader_id,
        filename=filename,
        content_type=content_type,
        size=12,
        storage_key=storage_key or f"tickets/{ticket_id}/abc123/{filename}",
    )
    db.add(attachment)
    db.flush()
    return attachment


def _download_url(ticket_id: int, attachment_id: int) -> str:
    return f"{TICKETS_URL}/{ticket_id}/attachments/{attachment_id}/download"


@pytest.fixture
def mock_storage(client: TestClient) -> MagicMock:
    storage = MagicMock(spec=StorageService)
    storage.generate_download_url.return_value = SIGNED_URL
    app.dependency_overrides[get_storage_service] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage_service, None)


# --- Auth -------------------------------------------------------------------


def test_download_url_requires_auth(client, db_session, mock_storage):
    customer = create_user(db_session, email="dl-noauth@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    attachment = _create_attachment(
        db_session, ticket_id=ticket.id, uploader_id=customer.id
    )

    res = client.get(_download_url(ticket.id, attachment.id))

    assert res.status_code == 401
    mock_storage.generate_download_url.assert_not_called()


# --- Happy path -------------------------------------------------------------


def test_owner_gets_short_lived_signed_url(client, db_session, mock_storage):
    customer = create_user(db_session, email="dl-owner@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    attachment = _create_attachment(
        db_session,
        ticket_id=ticket.id,
        uploader_id=customer.id,
        storage_key="tickets/1/unique/note.txt",
    )

    res = client.get(
        _download_url(ticket.id, attachment.id),
        headers=auth_header(customer),
    )

    assert res.status_code == 200
    body = res.json()
    assert body["url"] == SIGNED_URL
    assert body["expires_in"] == DOWNLOAD_URL_EXPIRY_SECONDS
    assert "storage_key" not in body

    mock_storage.generate_download_url.assert_called_once()
    kwargs = mock_storage.generate_download_url.call_args.kwargs
    assert kwargs["key"] == "tickets/1/unique/note.txt"
    assert kwargs["filename"] == "note.txt"


def test_assigned_agent_can_get_download_url(client, db_session, mock_storage):
    agent = create_user(db_session, email="dl-agent@test.com", role="agent")
    customer = create_user(db_session, email="dl-cust-agent@test.com", role="customer")
    ticket = create_ticket(
        db_session, requester_id=customer.id, assignee_id=agent.id
    )
    attachment = _create_attachment(
        db_session, ticket_id=ticket.id, uploader_id=customer.id
    )

    res = client.get(
        _download_url(ticket.id, attachment.id),
        headers=auth_header(agent),
    )

    assert res.status_code == 200
    assert res.json()["url"] == SIGNED_URL


def test_admin_can_get_download_url(client, db_session, mock_storage):
    admin = create_user(db_session, email="dl-admin@test.com", role="admin")
    customer = create_user(db_session, email="dl-cust-admin@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    attachment = _create_attachment(
        db_session, ticket_id=ticket.id, uploader_id=customer.id
    )

    res = client.get(
        _download_url(ticket.id, attachment.id),
        headers=auth_header(admin),
    )

    assert res.status_code == 200
    assert res.json()["url"] == SIGNED_URL


# --- Authorization & IDOR ---------------------------------------------------


def test_other_customer_cannot_get_download_url(client, db_session, mock_storage):
    owner = create_user(db_session, email="dl-owner2@test.com", role="customer")
    other = create_user(db_session, email="dl-other@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=owner.id)
    attachment = _create_attachment(
        db_session, ticket_id=ticket.id, uploader_id=owner.id
    )

    res = client.get(
        _download_url(ticket.id, attachment.id),
        headers=auth_header(other),
    )

    assert res.status_code == 403
    assert "url" not in res.json()
    mock_storage.generate_download_url.assert_not_called()


def test_unassigned_agent_cannot_get_download_url(client, db_session, mock_storage):
    agent = create_user(db_session, email="dl-unassigned@test.com", role="agent")
    customer = create_user(db_session, email="dl-cust-un@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    attachment = _create_attachment(
        db_session, ticket_id=ticket.id, uploader_id=customer.id
    )

    res = client.get(
        _download_url(ticket.id, attachment.id),
        headers=auth_header(agent),
    )

    assert res.status_code == 403
    mock_storage.generate_download_url.assert_not_called()


def test_download_unknown_ticket_returns_404(client, db_session, mock_storage):
    customer = create_user(db_session, email="dl-404t@test.com", role="customer")
    res = client.get(
        _download_url(99999, 1),
        headers=auth_header(customer),
    )
    assert res.status_code == 404
    mock_storage.generate_download_url.assert_not_called()


def test_download_unknown_attachment_returns_404(client, db_session, mock_storage):
    customer = create_user(db_session, email="dl-404a@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)

    res = client.get(
        _download_url(ticket.id, 99999),
        headers=auth_header(customer),
    )

    assert res.status_code == 404
    mock_storage.generate_download_url.assert_not_called()


def test_cannot_download_attachment_from_another_ticket(client, db_session, mock_storage):
    """IDOR guard: an attachment id from a different ticket returns 404."""
    customer = create_user(db_session, email="dl-cross@test.com", role="customer")
    ticket_a = create_ticket(db_session, requester_id=customer.id, title="A")
    ticket_b = create_ticket(db_session, requester_id=customer.id, title="B")
    attachment_b = _create_attachment(
        db_session, ticket_id=ticket_b.id, uploader_id=customer.id
    )

    res = client.get(
        _download_url(ticket_a.id, attachment_b.id),
        headers=auth_header(customer),
    )

    assert res.status_code == 404
    mock_storage.generate_download_url.assert_not_called()


# --- Storage service unit test ----------------------------------------------


def test_generate_download_url_uses_presign_client():
    upload_client = MagicMock()
    presign_client = MagicMock()
    presign_client.generate_presigned_url.return_value = SIGNED_URL
    service = StorageService(client=upload_client, presign_client=presign_client)

    url = service.generate_download_url(key="tickets/1/x/note.txt", filename="note.txt")

    assert url == SIGNED_URL
    presign_client.generate_presigned_url.assert_called_once()
    upload_client.generate_presigned_url.assert_not_called()


def test_generate_download_url_uses_presigned_get_with_expiry():
    fake_client = MagicMock()
    fake_client.generate_presigned_url.return_value = SIGNED_URL
    service = StorageService(client=fake_client)

    url = service.generate_download_url(key="tickets/1/x/note.txt", filename="note.txt")

    assert url == SIGNED_URL
    fake_client.generate_presigned_url.assert_called_once()
    args, kwargs = fake_client.generate_presigned_url.call_args
    assert args[0] == "get_object"
    assert kwargs["ExpiresIn"] == DOWNLOAD_URL_EXPIRY_SECONDS
    assert kwargs["Params"]["Key"] == "tickets/1/x/note.txt"
    assert 'filename="note.txt"' in kwargs["Params"]["ResponseContentDisposition"]
