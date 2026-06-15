from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.permissions import can_access_ticket, ensure_ticket_access
from app.models.ticket import Ticket
from app.models.user import User


def _user(role: str, user_id: int = 1) -> User:
    return User(
        id=user_id,
        email=f"{role}@test.com",
        password_hash="hash",
        full_name="Test",
        role=role,
    )


def _ticket(*, requester_id: int = 1, assignee_id: int | None = None) -> Ticket:
    return Ticket(
        id=1,
        title="Test ticket",
        description="",
        requester_id=requester_id,
        assignee_id=assignee_id,
    )


def test_admin_can_access_any_ticket():
    admin = _user("admin")
    ticket = _ticket(requester_id=99, assignee_id=88)
    assert can_access_ticket(admin, ticket) is True


def test_agent_can_access_assigned_ticket():
    agent = _user("agent", user_id=5)
    ticket = _ticket(requester_id=99, assignee_id=5)
    assert can_access_ticket(agent, ticket) is True


def test_agent_cannot_access_unassigned_ticket():
    agent = _user("agent", user_id=5)
    ticket = _ticket(requester_id=99, assignee_id=99)
    assert can_access_ticket(agent, ticket) is False


def test_customer_can_access_own_ticket():
    customer = _user("customer", user_id=3)
    ticket = _ticket(requester_id=3)
    assert can_access_ticket(customer, ticket) is True


def test_customer_cannot_access_other_ticket():
    customer = _user("customer", user_id=3)
    ticket = _ticket(requester_id=99)
    assert can_access_ticket(customer, ticket) is False


def test_ensure_ticket_access_raises_for_denied_customer():
    customer = _user("customer", user_id=3)
    ticket = _ticket(requester_id=99)
    with pytest.raises(HTTPException) as exc:
        ensure_ticket_access(customer, ticket)
    assert exc.value.status_code == 403
