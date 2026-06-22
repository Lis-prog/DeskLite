from __future__ import annotations

from tests.conftest import auth_header, create_ticket, create_user

WORKLOAD_URL = "/api/v1/metrics/agents/workload"


def test_admin_gets_active_ticket_count_per_agent(client, db_session):
    admin = create_user(db_session, email="workload-admin@test.com", role="admin")
    agent_a = create_user(
        db_session,
        email="workload-agent-a@test.com",
        role="agent",
        full_name="Agent A",
    )
    agent_b = create_user(
        db_session,
        email="workload-agent-b@test.com",
        role="agent",
        full_name="Agent B",
    )
    customer = create_user(db_session, email="workload-cust@test.com", role="customer")

    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Open for A",
        status="open",
        assignee_id=agent_a.id,
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="In progress for A",
        status="in_progress",
        assignee_id=agent_a.id,
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Resolved for A",
        status="resolved",
        assignee_id=agent_a.id,
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Open for B",
        status="open",
        assignee_id=agent_b.id,
    )

    res = client.get(WORKLOAD_URL, headers=auth_header(admin))
    assert res.status_code == 200
    by_id = {row["agent_id"]: row for row in res.json()}
    assert by_id[agent_a.id]["active_ticket_count"] == 2
    assert by_id[agent_b.id]["active_ticket_count"] == 1
    assert by_id[agent_a.id]["full_name"] == "Agent A"


def test_agent_with_no_active_tickets_shows_zero(client, db_session):
    admin = create_user(db_session, email="workload-zero-admin@test.com", role="admin")
    agent = create_user(db_session, email="workload-idle-agent@test.com", role="agent")
    customer = create_user(db_session, email="workload-zero-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Closed only",
        status="closed",
        assignee_id=agent.id,
    )

    res = client.get(WORKLOAD_URL, headers=auth_header(admin))
    assert res.status_code == 200
    row = next(item for item in res.json() if item["agent_id"] == agent.id)
    assert row["active_ticket_count"] == 0


def test_non_admin_forbidden(client, db_session):
    agent = create_user(db_session, email="workload-forbidden-agent@test.com", role="agent")
    customer = create_user(db_session, email="workload-forbidden-cust@test.com", role="customer")

    for user in (agent, customer):
        res = client.get(WORKLOAD_URL, headers=auth_header(user))
        assert res.status_code == 403


def test_workload_requires_authentication(client):
    res = client.get(WORKLOAD_URL)
    assert res.status_code == 401


def test_empty_agent_list_returns_empty_array(client, db_session):
    admin = create_user(db_session, email="workload-empty-admin@test.com", role="admin")

    res = client.get(WORKLOAD_URL, headers=auth_header(admin))
    assert res.status_code == 200
    assert res.json() == []
