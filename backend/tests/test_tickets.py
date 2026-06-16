from __future__ import annotations

from tests.conftest import make_ticket, make_token, make_user


def _auth(token: str) -> dict[str, str]:
    return {"Cookie": f"access_token={token}"}


def test_owner_can_update_whitelisted_fields(client, db):
    owner = make_user(db, role="customer", email="owner@test.com")
    ticket = make_ticket(db, requester_id=owner.id)

    res = client.patch(
        f"/api/v1/tickets/{ticket.id}",
        json={"title": "Updated title", "priority": "high"},
        headers=_auth(make_token(owner.id, "customer")),
    )

    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "Updated title"
    assert body["priority"] == "high"
    # Untouched field stays the same.
    assert body["description"] == "Original description"


def test_ownership_cannot_be_changed_by_client(client, db):
    """requester_id is not whitelisted → 422, and it must stay unchanged."""
    owner = make_user(db, role="customer", email="owner2@test.com")
    ticket = make_ticket(db, requester_id=owner.id)

    res = client.patch(
        f"/api/v1/tickets/{ticket.id}",
        json={"title": "x", "requester_id": 999},
        headers=_auth(make_token(owner.id, "customer")),
    )

    assert res.status_code == 422
    db.refresh(ticket)
    assert ticket.requester_id == owner.id
    assert ticket.title == "Original title"


def test_status_cannot_be_set_via_update(client, db):
    """status moves only through the transition endpoint → 422 here."""
    owner = make_user(db, role="customer", email="owner3@test.com")
    ticket = make_ticket(db, requester_id=owner.id)

    res = client.patch(
        f"/api/v1/tickets/{ticket.id}",
        json={"status": "closed"},
        headers=_auth(make_token(owner.id, "customer")),
    )

    assert res.status_code == 422
    db.refresh(ticket)
    assert ticket.status == "open"


def test_customer_cannot_update_another_users_ticket(client, db):
    """IDOR guard: customer B editing customer A's ticket gets 404, no data leak."""
    owner = make_user(db, role="customer", email="a@test.com")
    other = make_user(db, role="customer", email="b@test.com")
    ticket = make_ticket(db, requester_id=owner.id)

    res = client.patch(
        f"/api/v1/tickets/{ticket.id}",
        json={"title": "hijacked"},
        headers=_auth(make_token(other.id, "customer")),
    )

    assert res.status_code == 404
    assert "title" not in res.json()
    db.refresh(ticket)
    assert ticket.title == "Original title"


def test_admin_can_update_any_ticket(client, db):
    owner = make_user(db, role="customer", email="cust@test.com")
    admin = make_user(db, role="admin", email="admin@test.com")
    ticket = make_ticket(db, requester_id=owner.id)

    res = client.patch(
        f"/api/v1/tickets/{ticket.id}",
        json={"priority": "urgent"},
        headers=_auth(make_token(admin.id, "admin")),
    )

    assert res.status_code == 200
    assert res.json()["priority"] == "urgent"


def test_agent_can_update_only_assigned_ticket(client, db):
    owner = make_user(db, role="customer", email="cust2@test.com")
    agent = make_user(db, role="agent", email="agent@test.com")
    assigned = make_ticket(db, requester_id=owner.id, assignee_id=agent.id)
    unassigned = make_ticket(db, requester_id=owner.id)

    ok = client.patch(
        f"/api/v1/tickets/{assigned.id}",
        json={"title": "agent edit"},
        headers=_auth(make_token(agent.id, "agent")),
    )
    assert ok.status_code == 200

    denied = client.patch(
        f"/api/v1/tickets/{unassigned.id}",
        json={"title": "nope"},
        headers=_auth(make_token(agent.id, "agent")),
    )
    assert denied.status_code == 404


def test_update_unknown_ticket_returns_404(client, db):
    user = make_user(db, role="admin", email="admin2@test.com")
    res = client.patch(
        "/api/v1/tickets/999999",
        json={"title": "x"},
        headers=_auth(make_token(user.id, "admin")),
    )
    assert res.status_code == 404


def test_update_requires_authentication(client, db):
    owner = make_user(db, role="customer", email="owner4@test.com")
    ticket = make_ticket(db, requester_id=owner.id)

    res = client.patch(f"/api/v1/tickets/{ticket.id}", json={"title": "x"})
    assert res.status_code == 401


def test_empty_update_returns_400(client, db):
    owner = make_user(db, role="customer", email="owner5@test.com")
    ticket = make_ticket(db, requester_id=owner.id)

    res = client.patch(
        f"/api/v1/tickets/{ticket.id}",
        json={},
        headers=_auth(make_token(owner.id, "customer")),
    )
    assert res.status_code == 400
