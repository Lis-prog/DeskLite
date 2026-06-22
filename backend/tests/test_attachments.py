from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.file_validation import (
    MAX_FILE_SIZE_BYTES,
    FileValidationError,
    validate_upload,
)
from app.core.storage import StorageService, get_storage_service
from app.main import app
from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"


def _upload(client, ticket_id: int, *, filename: str, content: bytes, content_type: str, user):
    return client.post(
        f"{TICKETS_URL}/{ticket_id}/attachments",
        files={"file": (filename, content, content_type)},
        headers=auth_header(user),
    )


@pytest.fixture
def mock_storage(client: TestClient) -> MagicMock:
    storage = MagicMock(spec=StorageService)
    app.dependency_overrides[get_storage_service] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage_service, None)


# --- Validation unit tests ----------------------------------------------------


def test_validate_upload_accepts_allowed_pdf():
    validate_upload("report.pdf", "application/pdf", 1024)


def test_validate_upload_rejects_disallowed_extension():
    with pytest.raises(FileValidationError, match="not allowed"):
        validate_upload("malware.exe", "application/octet-stream", 100)


def test_validate_upload_rejects_disallowed_content_type():
    with pytest.raises(FileValidationError, match="Content type"):
        validate_upload("notes.txt", "application/x-msdownload", 100)


def test_validate_upload_rejects_empty_file():
    with pytest.raises(FileValidationError, match="empty"):
        validate_upload("empty.pdf", "application/pdf", 0)


def test_validate_upload_rejects_oversized_file():
    with pytest.raises(FileValidationError, match="maximum size"):
        validate_upload("big.pdf", "application/pdf", MAX_FILE_SIZE_BYTES + 1)


# --- Upload endpoint ----------------------------------------------------------


def test_upload_attachment_requires_auth(client, db_session):
    customer = create_user(db_session, email="att-noauth@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.post(
        f"{TICKETS_URL}/{ticket.id}/attachments",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 401


def test_upload_attachment_happy_path(client, db_session, mock_storage):
    customer = create_user(db_session, email="att-ok@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    content = b"Plain text attachment"

    res = _upload(
        client,
        ticket.id,
        filename="note.txt",
        content=content,
        content_type="text/plain",
        user=customer,
    )

    assert res.status_code == 201
    body = res.json()
    assert body["ticket_id"] == ticket.id
    assert body["uploader_id"] == customer.id
    assert body["filename"] == "note.txt"
    assert body["content_type"] == "text/plain"
    assert body["size"] == len(content)
    assert "storage_key" not in body
    assert "id" in body
    assert "created_at" in body

    mock_storage.upload.assert_called_once()
    kwargs = mock_storage.upload.call_args.kwargs
    assert kwargs["body"] == content
    assert kwargs["content_type"] == "text/plain"
    assert kwargs["key"].startswith(f"tickets/{ticket.id}/")


def test_upload_rejects_disallowed_extension(client, db_session, mock_storage):
    customer = create_user(db_session, email="att-badext@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)

    res = _upload(
        client,
        ticket.id,
        filename="virus.exe",
        content=b"MZ",
        content_type="application/octet-stream",
        user=customer,
    )

    assert res.status_code == 400
    assert "not allowed" in res.json()["detail"].lower()
    mock_storage.upload.assert_not_called()


def test_upload_rejects_oversized_file(client, db_session, mock_storage):
    customer = create_user(db_session, email="att-big@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)

    res = _upload(
        client,
        ticket.id,
        filename="large.pdf",
        content=oversized,
        content_type="application/pdf",
        user=customer,
    )

    assert res.status_code == 400
    assert "maximum size" in res.json()["detail"].lower()
    mock_storage.upload.assert_not_called()


def test_cannot_upload_to_inaccessible_ticket(client, db_session, mock_storage):
    owner = create_user(db_session, email="att-owner@test.com", role="customer")
    other = create_user(db_session, email="att-other@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=owner.id)

    res = _upload(
        client,
        ticket.id,
        filename="note.txt",
        content=b"nope",
        content_type="text/plain",
        user=other,
    )

    assert res.status_code == 403
    mock_storage.upload.assert_not_called()


def test_upload_unknown_ticket_returns_404(client, db_session, mock_storage):
    customer = create_user(db_session, email="att-404@test.com", role="customer")
    res = _upload(
        client,
        99999,
        filename="note.txt",
        content=b"hello",
        content_type="text/plain",
        user=customer,
    )
    assert res.status_code == 404
    mock_storage.upload.assert_not_called()
