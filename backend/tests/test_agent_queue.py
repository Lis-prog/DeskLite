from __future__ import annotations

from tests.conftest import auth_header, create_ticket, create_user

QUEUE_URL = "/api/v1/tickets/queue"


def test_queue_requires_auth(client, db_session):
    res = client.get(QUEUE_URL)
    assert res.status_code == 401


def test_queue_returns_only_tickets_assigned_to_caller(client, db_session):
    agent = create_user(db_session, email="q-agent@test.com", role="agent")
    other_agent = create_user(db_session, email="q-other@test.com", role="agent")
    customer = create_user(db_session, email="q-cust@test.com", role="customer")

    mine = create_ticket(
        db_session, requester_id=customer.id, assignee_id=agent.id, title="Mine"
    )
    create_ticket(
        db_session, requester_id=customer.id, assignee_id=other_agent.id, title="Theirs"
    )
    create_ticket(db_session, requester_id=customer.id, title="Unassigned")

    res = client.get(QUEUE_URL, headers=auth_header(agent))
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["id"] == mine.id
    assert body[0]["assignee_id"] == agent.id


def test_queue_empty_when_no_assignments(client, db_session):
    agent = create_user(db_session, email="q-empty@test.com", role="agent")
    res = client.get(QUEUE_URL, headers=auth_header(agent))
    assert res.status_code == 200
    assert res.json() == []


def test_queue_forbidden_for_customer(client, db_session):
    customer = create_user(db_session, email="q-cust403@test.com", role="customer")
    res = client.get(QUEUE_URL, headers=auth_header(customer))
    assert res.status_code == 403


def test_queue_forbidden_for_admin(client, db_session):
    admin = create_user(db_session, email="q-admin403@test.com", role="admin")
    res = client.get(QUEUE_URL, headers=auth_header(admin))
    assert res.status_code == 403
