from __future__ import annotations

from tests.conftest import auth_header, create_ticket, create_user

METRICS_URL = "/api/v1/metrics/tickets"


def test_admin_sees_all_ticket_counts(client, db_session):
    admin = create_user(db_session, email="metrics-admin@test.com", role="admin")
    customer = create_user(db_session, email="metrics-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Open unassigned",
        status="open",
        priority="high",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Closed assigned",
        status="closed",
        priority="low",
        assignee_id=create_user(db_session, email="metrics-agent@test.com", role="agent").id,
    )

    res = client.get(METRICS_URL, headers=auth_header(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert body["by_status"]["open"] == 1
    assert body["by_status"]["closed"] == 1
    assert body["by_status"]["in_progress"] == 0
    assert body["by_priority"]["high"] == 1
    assert body["by_priority"]["low"] == 1
    assert body["unassigned"] == 1


def test_customer_sees_only_own_ticket_counts(client, db_session):
    customer = create_user(db_session, email="metrics-own-cust@test.com", role="customer")
    other = create_user(db_session, email="metrics-other-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Mine",
        status="open",
        priority="medium",
    )
    create_ticket(
        db_session,
        requester_id=other.id,
        title="Theirs",
        status="open",
        priority="urgent",
    )

    res = client.get(METRICS_URL, headers=auth_header(customer))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["by_status"]["open"] == 1
    assert body["by_priority"]["medium"] == 1
    assert body["by_priority"]["urgent"] == 0


def test_agent_sees_only_assigned_ticket_counts(client, db_session):
    agent = create_user(db_session, email="metrics-agent-scope@test.com", role="agent")
    other_agent = create_user(db_session, email="metrics-agent-other@test.com", role="agent")
    customer = create_user(db_session, email="metrics-agent-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Assigned to me",
        status="in_progress",
        priority="high",
        assignee_id=agent.id,
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Assigned to other",
        status="open",
        priority="low",
        assignee_id=other_agent.id,
    )

    res = client.get(METRICS_URL, headers=auth_header(agent))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["by_status"]["in_progress"] == 1
    assert body["by_status"]["open"] == 0
    assert body["by_priority"]["high"] == 1


def test_metrics_requires_authentication(client):
    res = client.get(METRICS_URL)
    assert res.status_code == 401


def test_empty_metrics_return_zero_buckets(client, db_session):
    admin = create_user(db_session, email="metrics-empty-admin@test.com", role="admin")

    res = client.get(METRICS_URL, headers=auth_header(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 0
    assert body["unassigned"] == 0
    assert set(body["by_status"].keys()) == {"open", "in_progress", "resolved", "closed"}
    assert set(body["by_priority"].keys()) == {"low", "medium", "high", "urgent"}
    assert all(count == 0 for count in body["by_status"].values())
    assert all(count == 0 for count in body["by_priority"].values())
