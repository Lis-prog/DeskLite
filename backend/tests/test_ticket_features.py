from __future__ import annotations

from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"
ADMIN_ASSIGN_URL = "/api/v1/admin/tickets/{ticket_id}/assignee"


# --- Comments -----------------------------------------------------------------


def test_list_comments_requires_auth(client, db_session):
    customer = create_user(db_session, email="cmt-noauth@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.get(f"{TICKETS_URL}/{ticket.id}/comments")
    assert res.status_code == 401


def test_post_comment_sets_author_from_jwt(client, db_session):
    customer = create_user(db_session, email="cmt-author@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.post(
        f"{TICKETS_URL}/{ticket.id}/comments",
        json={"body": "Still broken after reboot."},
        headers=auth_header(customer),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["author_id"] == customer.id
    assert body["author"]["full_name"] == customer.full_name
    assert body["body"] == "Still broken after reboot."


def test_comment_body_is_sanitized(client, db_session):
    customer = create_user(db_session, email="cmt-xss@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.post(
        f"{TICKETS_URL}/{ticket.id}/comments",
        json={"body": "<script>alert(1)</script>Hello"},
        headers=auth_header(customer),
    )
    assert res.status_code == 201
    assert res.json()["body"] == "Hello"


def test_comment_rejects_markup_only_body(client, db_session):
    customer = create_user(db_session, email="cmt-empty@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    res = client.post(
        f"{TICKETS_URL}/{ticket.id}/comments",
        json={"body": "<script>alert(1)</script>"},
        headers=auth_header(customer),
    )
    assert res.status_code == 422


def test_cannot_comment_on_inaccessible_ticket(client, db_session):
    owner = create_user(db_session, email="cmt-owner@test.com", role="customer")
    other = create_user(db_session, email="cmt-other@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=owner.id)
    res = client.post(
        f"{TICKETS_URL}/{ticket.id}/comments",
        json={"body": "Should not post"},
        headers=auth_header(other),
    )
    assert res.status_code == 403


def test_list_comments_returns_only_for_accessible_ticket(client, db_session):
    customer = create_user(db_session, email="cmt-list@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)
    client.post(
        f"{TICKETS_URL}/{ticket.id}/comments",
        json={"body": "First note"},
        headers=auth_header(customer),
    )
    res = client.get(
        f"{TICKETS_URL}/{ticket.id}/comments",
        headers=auth_header(customer),
    )
    assert res.status_code == 200
    comments = res.json()
    assert len(comments) == 1
    assert comments[0]["body"] == "First note"


# --- Assignment (admin) -------------------------------------------------------


def test_admin_can_assign_ticket_to_agent(client, db_session):
    admin = create_user(db_session, email="asgn-admin@test.com", role="admin")
    agent = create_user(db_session, email="asgn-agent@test.com", role="agent")
    customer = create_user(db_session, email="asgn-cust@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)

    res = client.patch(
        ADMIN_ASSIGN_URL.format(ticket_id=ticket.id),
        json={"assignee_id": agent.id},
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    assert res.json()["assignee_id"] == agent.id


def test_admin_can_unassign_with_explicit_null(client, db_session):
    admin = create_user(db_session, email="asgn-unadmin@test.com", role="admin")
    agent = create_user(db_session, email="asgn-unagent@test.com", role="agent")
    customer = create_user(db_session, email="asgn-uncust@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=agent.id,
    )

    res = client.patch(
        ADMIN_ASSIGN_URL.format(ticket_id=ticket.id),
        json={"assignee_id": None},
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    assert res.json()["assignee_id"] is None


def test_assign_rejects_empty_body(client, db_session):
    admin = create_user(db_session, email="asgn-empty@test.com", role="admin")
    customer = create_user(db_session, email="asgn-emptycust@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)

    res = client.patch(
        ADMIN_ASSIGN_URL.format(ticket_id=ticket.id),
        json={},
        headers=auth_header(admin),
    )
    assert res.status_code == 422


def test_assign_rejects_non_agent_assignee(client, db_session):
    admin = create_user(db_session, email="asgn-badadmin@test.com", role="admin")
    customer = create_user(db_session, email="asgn-badcust@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id)

    res = client.patch(
        ADMIN_ASSIGN_URL.format(ticket_id=ticket.id),
        json={"assignee_id": customer.id},
        headers=auth_header(admin),
    )
    assert res.status_code == 400


def test_customer_cannot_assign_ticket(client, db_session):
    customer = create_user(db_session, email="asgn-denied@test.com", role="customer")
    agent = create_user(db_session, email="asgn-deniedagent@test.com", role="agent")
    ticket = create_ticket(db_session, requester_id=customer.id)

    res = client.patch(
        ADMIN_ASSIGN_URL.format(ticket_id=ticket.id),
        json={"assignee_id": agent.id},
        headers=auth_header(customer),
    )
    assert res.status_code == 403


# --- Satisfaction -------------------------------------------------------------


def test_requester_can_rate_closed_ticket(client, db_session):
    customer = create_user(db_session, email="sat-cust@test.com", role="customer")
    ticket = create_ticket(
        db_session,
        requester_id=customer.id,
        status="closed",
    )

    res = client.post(
        f"{TICKETS_URL}/{ticket.id}/satisfaction",
        json={"rating": 5},
        headers=auth_header(customer),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["rating"] == 5
    assert "submitted_at" in body


def test_cannot_rate_open_ticket(client, db_session):
    customer = create_user(db_session, email="sat-open@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id, status="open")

    res = client.post(
        f"{TICKETS_URL}/{ticket.id}/satisfaction",
        json={"rating": 4},
        headers=auth_header(customer),
    )
    assert res.status_code == 400


def test_non_requester_cannot_rate_ticket(client, db_session):
    owner = create_user(db_session, email="sat-owner@test.com", role="customer")
    other = create_user(db_session, email="sat-other@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=owner.id, status="closed")

    res = client.post(
        f"{TICKETS_URL}/{ticket.id}/satisfaction",
        json={"rating": 3},
        headers=auth_header(other),
    )
    assert res.status_code == 403


def test_get_satisfaction_returns_null_when_missing(client, db_session):
    customer = create_user(db_session, email="sat-get@test.com", role="customer")
    ticket = create_ticket(db_session, requester_id=customer.id, status="closed")

    res = client.get(
        f"{TICKETS_URL}/{ticket.id}/satisfaction",
        headers=auth_header(customer),
    )
    assert res.status_code == 200
    assert res.json() is None
