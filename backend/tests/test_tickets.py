from __future__ import annotations

from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"


def test_create_ticket_requires_auth(client):
    res = client.post(
        TICKETS_URL,
        json={"title": "Broken laptop", "description": "Won't boot", "priority": "high"},
    )
    assert res.status_code == 401


def test_create_ticket_returns_201_with_ticket_read(client, db_session):
    customer = create_user(db_session, email="cust@test.com", role="customer")
    res = client.post(
        TICKETS_URL,
        json={
            "title": "Broken laptop",
            "description": "Won't boot after update",
            "priority": "high",
        },
        headers=auth_header(customer),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Broken laptop"
    assert body["description"] == "Won't boot after update"
    assert body["priority"] == "high"
    assert body["status"] == "open"
    assert body["requester_id"] == customer.id
    assert body["assignee_id"] is None
    assert body["id"] > 0
    assert "created_at" in body
    assert "updated_at" in body


def test_create_ticket_sets_requester_from_jwt_not_body(client, db_session):
    """Mass-assignment guard: requester_id in the body is rejected (422)."""
    customer = create_user(db_session, email="cust2@test.com", role="customer")
    other = create_user(db_session, email="other@test.com", role="customer")
    res = client.post(
        TICKETS_URL,
        json={
            "title": "Attempted spoof",
            "description": "",
            "priority": "medium",
            "requester_id": other.id,
        },
        headers=auth_header(customer),
    )
    assert res.status_code == 422


def test_create_ticket_rejects_status_in_body(client, db_session):
    customer = create_user(db_session, email="cust3@test.com", role="customer")
    res = client.post(
        TICKETS_URL,
        json={
            "title": "Status spoof",
            "description": "",
            "priority": "medium",
            "status": "closed",
        },
        headers=auth_header(customer),
    )
    assert res.status_code == 422


def test_create_ticket_rejects_assignee_in_body(client, db_session):
    customer = create_user(db_session, email="cust4@test.com", role="customer")
    agent = create_user(db_session, email="agent@test.com", role="agent")
    res = client.post(
        TICKETS_URL,
        json={
            "title": "Assignee spoof",
            "description": "",
            "priority": "medium",
            "assignee_id": agent.id,
        },
        headers=auth_header(customer),
    )
    assert res.status_code == 422


def test_create_ticket_rejects_empty_title(client, db_session):
    customer = create_user(db_session, email="cust5@test.com", role="customer")
    res = client.post(
        TICKETS_URL,
        json={"title": "", "description": "No title", "priority": "low"},
        headers=auth_header(customer),
    )
    assert res.status_code == 422


def test_create_ticket_defaults_priority_to_medium(client, db_session):
    customer = create_user(db_session, email="cust6@test.com", role="customer")
    res = client.post(
        TICKETS_URL,
        json={"title": "Minimal ticket", "description": ""},
        headers=auth_header(customer),
    )
    assert res.status_code == 201
    assert res.json()["priority"] == "medium"


def test_create_ticket_allowed_for_any_authenticated_role(client, db_session):
    for role in ("customer", "agent", "admin"):
        user = create_user(db_session, email=f"{role}@test.com", role=role)
        res = client.post(
            TICKETS_URL,
            json={"title": f"Ticket from {role}", "description": ""},
            headers=auth_header(user),
        )
        assert res.status_code == 201
        assert res.json()["requester_id"] == user.id


# --- List -------------------------------------------------------------------

def test_list_tickets_requires_auth(client):
    res = client.get(TICKETS_URL)
    assert res.status_code == 401


def test_list_tickets_customer_sees_own_only(client, db_session):
    customer_a = create_user(db_session, email="a@test.com", role="customer")
    customer_b = create_user(db_session, email="b@test.com", role="customer")
    own = create_ticket(db_session, requester_id=customer_a.id, title="Mine")
    create_ticket(db_session, requester_id=customer_b.id, title="Theirs")

    res = client.get(TICKETS_URL, headers=auth_header(customer_a))
    assert res.status_code == 200
    titles = {t["title"] for t in res.json()}
    assert titles == {"Mine"}
    assert res.json()[0]["id"] == own.id


def test_list_tickets_agent_sees_assigned_only(client, db_session):
    agent = create_user(db_session, email="agent@test.com", role="agent")
    customer = create_user(db_session, email="cust@test.com", role="customer")
    assigned = create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=agent.id,
        title="Assigned to me",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=None,
        title="Unassigned",
    )

    res = client.get(TICKETS_URL, headers=auth_header(agent))
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["id"] == assigned.id
    assert body[0]["title"] == "Assigned to me"


def test_list_tickets_admin_sees_all(client, db_session):
    admin = create_user(db_session, email="admin@test.com", role="admin")
    customer = create_user(db_session, email="cust2@test.com", role="customer")
    create_ticket(db_session, requester_id=customer.id, title="Admin visibility one")
    create_ticket(db_session, requester_id=customer.id, title="Admin visibility two")

    res = client.get(TICKETS_URL, headers=auth_header(admin))
    assert res.status_code == 200
    titles = {t["title"] for t in res.json()}
    assert "Admin visibility one" in titles
    assert "Admin visibility two" in titles


# --- Get by id --------------------------------------------------------------

def test_get_ticket_requires_auth(client, db_session):
    customer = create_user(db_session, email="anon@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.get(f"{TICKETS_URL}/{ticket.id}")
    assert res.status_code == 401


def test_get_ticket_owner_can_read(client, db_session):
    customer = create_user(db_session, email="owner@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        title="My ticket",
    )
    res = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_header(customer))
    assert res.status_code == 200
    assert res.json()["title"] == "My ticket"

def test_assigned_agent_can_read_ticket(client, db_session):
    agent = create_user(db_session, email="agent-read@test.com", role="agent")
    customer = create_user(db_session, email="agent-cust@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=agent.id,
        title="Assigned ticket",
    )

    res = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_header(agent))

    assert res.status_code == 200
    assert res.json()["title"] == "Assigned ticket"

def test_unassigned_agent_cannot_read_ticket(client, db_session):
    agent = create_user(db_session, email="agent-denied@test.com", role="agent")
    other_agent = create_user(db_session, email="other-agent@test.com", role="agent")
    customer = create_user(db_session, email="agent-owner@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=other_agent.id,
        title="Other agent ticket",
    )

    res = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_header(agent))

    assert res.status_code == 403
    assert "title" not in res.json()

def test_get_ticket_not_found(client, db_session):
    customer = create_user(db_session, email="missing@test.com", role="customer")
    res = client.get(f"{TICKETS_URL}/99999", headers=auth_header(customer))
    assert res.status_code == 404


def test_customer_cannot_read_another_users_ticket(client, db_session):
    owner = create_user(db_session, email="owner2@test.com", role="customer")
    other = create_user(db_session, email="other@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=owner.id, title="Private")

    res = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_header(other))
    assert res.status_code == 403
    assert "title" not in res.json()


def test_admin_can_read_any_ticket(client, db_session):
    admin = create_user(db_session, email="admin2@test.com", role="admin")
    customer = create_user(db_session, email="cust3@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id, title="Any")

    res = client.get(f"{TICKETS_URL}/{ticket.id}", headers=auth_header(admin))
    assert res.status_code == 200
    assert res.json()["title"] == "Any"


# --- Update -----------------------------------------------------------------

def test_update_ticket_requires_auth(client, db_session):
    customer = create_user(db_session, email="upd-noauth@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.patch(f"{TICKETS_URL}/{ticket.id}", json={"title": "x"})
    assert res.status_code == 401


def test_owner_can_update_whitelisted_fields(client, db_session):
    customer = create_user(db_session, email="upd-owner@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        title="Old title",
        description="Keep me",
    )
    res = client.patch(
        f"{TICKETS_URL}/{ticket.id}",
        json={"title": "New title", "priority": "high"},
        headers=auth_header(customer),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "New title"
    assert body["priority"] == "high"
    # Untouched field is preserved.
    assert body["description"] == "Keep me"


def test_update_rejects_requester_id_in_body(client, db_session):
    """Ownership cannot be changed by the client (mass-assignment guard)."""
    customer = create_user(db_session, email="upd-mass@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.patch(
        f"{TICKETS_URL}/{ticket.id}",
        json={"title": "x", "requester_id": 999},
        headers=auth_header(customer),
    )
    assert res.status_code == 422


def test_update_rejects_status_in_body(client, db_session):
    """Status moves only through the dedicated transition endpoint."""
    customer = create_user(db_session, email="upd-status@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.patch(
        f"{TICKETS_URL}/{ticket.id}",
        json={"status": "closed"},
        headers=auth_header(customer),
    )
    assert res.status_code == 422


def test_customer_cannot_update_another_users_ticket(client, db_session):
    """IDOR guard: editing someone else's ticket returns 403, no data leak."""
    owner = create_user(db_session, email="upd-owner2@test.com", role="customer")
    other = create_user(db_session, email="upd-other@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=owner.id, title="Private")
    res = client.patch(
        f"{TICKETS_URL}/{ticket.id}",
        json={"title": "hijacked"},
        headers=auth_header(other),
    )
    assert res.status_code == 403
    assert "title" not in res.json()


def test_admin_can_update_any_ticket(client, db_session):
    admin = create_user(db_session, email="upd-admin@test.com", role="admin")
    customer = create_user(db_session, email="upd-cust@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.patch(
        f"{TICKETS_URL}/{ticket.id}",
        json={"priority": "urgent"},
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    assert res.json()["priority"] == "urgent"


def test_agent_can_update_only_assigned_ticket(client, db_session):
    agent = create_user(db_session, email="upd-agent@test.com", role="agent")
    customer = create_user(db_session, email="upd-cust2@test.com", role="customer")
    assigned = create_ticket(db_session, requester_id=customer.id, assignee_id=agent.id)
    unassigned = create_ticket(db_session, requester_id=customer.id)

    ok = client.patch(
        f"{TICKETS_URL}/{assigned.id}",
        json={"title": "agent edit"},
        headers=auth_header(agent),
    )
    assert ok.status_code == 200

    denied = client.patch(
        f"{TICKETS_URL}/{unassigned.id}",
        json={"title": "nope"},
        headers=auth_header(agent),
    )
    assert denied.status_code == 403


def test_update_unknown_ticket_returns_404(client, db_session):
    admin = create_user(db_session, email="upd-404@test.com", role="admin")
    res = client.patch(
        f"{TICKETS_URL}/99999",
        json={"title": "x"},
        headers=auth_header(admin),
    )
    assert res.status_code == 404
