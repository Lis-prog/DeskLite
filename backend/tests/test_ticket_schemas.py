from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.ticket import (
    TicketCreate,
    TicketRead,
    TicketStatusUpdate,
    TicketUpdate,
)

# --- TicketCreate: whitelist + validation -------------------------------

def test_create_minimal_applies_defaults():
    ticket = TicketCreate(title="Printer is broken")
    assert ticket.description == ""
    assert ticket.priority == "medium"


def test_create_accepts_valid_priority():
    ticket = TicketCreate(title="VPN down", priority="urgent")
    assert ticket.priority == "urgent"


def test_create_requires_title():
    with pytest.raises(ValidationError):
        TicketCreate(description="no title given")


def test_create_rejects_empty_title():
    with pytest.raises(ValidationError):
        TicketCreate(title="")


def test_create_rejects_overlong_title():
    with pytest.raises(ValidationError):
        TicketCreate(title="x" * 201)


def test_create_rejects_invalid_priority():
    with pytest.raises(ValidationError):
        TicketCreate(title="ok", priority="critical")


@pytest.mark.parametrize("field", ["status", "requester_id", "assignee_id", "id"])
def test_create_forbids_server_controlled_fields(field):
    """Anti mass-assignment: a client cannot set identity/status/ownership."""
    with pytest.raises(ValidationError):
        TicketCreate(title="ok", **{field: 1})


# --- TicketUpdate: partial + whitelist ----------------------------------

def test_update_allows_empty_payload():
    update = TicketUpdate()
    assert update.model_dump(exclude_unset=True) == {}


def test_update_partial_single_field():
    update = TicketUpdate(priority="low")
    assert update.model_dump(exclude_unset=True) == {"priority": "low"}


def test_update_rejects_invalid_priority():
    with pytest.raises(ValidationError):
        TicketUpdate(priority="someday")


def test_update_forbids_status_field():
    """Status must go through the dedicated transition payload, not here."""
    with pytest.raises(ValidationError):
        TicketUpdate(status="closed")


@pytest.mark.parametrize("field", ["requester_id", "assignee_id", "id"])
def test_update_forbids_server_controlled_fields(field):
    with pytest.raises(ValidationError):
        TicketUpdate(**{field: 1})


# --- TicketStatusUpdate -------------------------------------------------

def test_status_update_accepts_valid_status():
    assert TicketStatusUpdate(status="in_progress").status == "in_progress"


def test_status_update_rejects_invalid_status():
    with pytest.raises(ValidationError):
        TicketStatusUpdate(status="done")


# --- TicketRead: reads straight off the ORM object ----------------------

def test_read_from_attributes():
    now = datetime.now(UTC)
    row = SimpleNamespace(
        id=7,
        title="Laptop won't boot",
        description="black screen",
        status="open",
        priority="high",
        requester_id=3,
        assignee_id=None,
        created_at=now,
        updated_at=now,
        resolved_at=None,
    )
    read = TicketRead.model_validate(row)
    assert read.id == 7
    assert read.status == "open"
    assert read.assignee_id is None
