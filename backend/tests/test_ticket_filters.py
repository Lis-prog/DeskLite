from __future__ import annotations

from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"


def test_filter_by_status_respects_role_scope(client, db_session):
    customer = create_user(db_session, email="filter-cust@test.com", role="customer")
    other = create_user(db_session, email="filter-other@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="My open",
        status="open",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="My closed",
        status="closed",
    )
    create_ticket(
        db_session,
        requester_id=other.id,
        title="Their open",
        status="open",
    )

    res = client.get(
        f"{TICKETS_URL}?status=open",
        headers=auth_header(customer),
    )
    assert res.status_code == 200
    titles = {t["title"] for t in res.json()}
    assert titles == {"My open"}


def test_filter_by_priority(client, db_session):
    admin = create_user(db_session, email="filter-admin@test.com", role="admin")
    customer = create_user(db_session, email="filter-pri-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="High priority",
        priority="high",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Low priority",
        priority="low",
    )

    res = client.get(
        f"{TICKETS_URL}?priority=high",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    titles = {t["title"] for t in res.json()}
    assert titles == {"High priority"}


def test_admin_can_filter_by_assignee_id(client, db_session):
    admin = create_user(db_session, email="assign-admin@test.com", role="admin")
    agent_a = create_user(db_session, email="agent-a@test.com", role="agent")
    agent_b = create_user(db_session, email="agent-b@test.com", role="agent")
    customer = create_user(db_session, email="assign-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=agent_a.id,
        title="Assigned to A",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=agent_b.id,
        title="Assigned to B",
    )

    res = client.get(
        f"{TICKETS_URL}?assignee_id={agent_a.id}",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    titles = {t["title"] for t in res.json()}
    assert titles == {"Assigned to A"}


def test_admin_can_filter_unassigned(client, db_session):
    admin = create_user(db_session, email="unassigned-admin@test.com", role="admin")
    agent = create_user(db_session, email="unassigned-agent@test.com", role="agent")
    customer = create_user(db_session, email="unassigned-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=agent.id,
        title="Has assignee",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=None,
        title="No assignee",
    )

    res = client.get(
        f"{TICKETS_URL}?unassigned=true",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    titles = {t["title"] for t in res.json()}
    assert titles == {"No assignee"}


def test_non_admin_cannot_filter_by_assignee(client, db_session):
    agent = create_user(db_session, email="assign-deny-agent@test.com", role="agent")
    customer = create_user(db_session, email="assign-deny-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=agent.id,
        title="Agent ticket",
    )

    res = client.get(
        f"{TICKETS_URL}?assignee_id={agent.id}",
        headers=auth_header(agent),
    )
    assert res.status_code == 403

    res2 = client.get(
        f"{TICKETS_URL}?unassigned=true",
        headers=auth_header(customer),
    )
    assert res2.status_code == 403


def test_admin_scope_mine(client, db_session):
    admin = create_user(db_session, email="scope-admin@test.com", role="admin")
    customer = create_user(db_session, email="scope-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=admin.id,
        title="Admin requested",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        assignee_id=admin.id,
        title="Admin assigned",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Unrelated",
    )

    res = client.get(
        f"{TICKETS_URL}?scope=mine",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    titles = {t["title"] for t in res.json()}
    assert titles == {"Admin requested", "Admin assigned"}


def test_search_matches_title_and_description(client, db_session):
    admin = create_user(db_session, email="search-admin@test.com", role="admin")
    customer = create_user(db_session, email="search-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Billing issue",
        description="Invoice mismatch",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Hardware",
        description="Broken billing portal link",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Other",
        description="Unrelated problem",
    )

    res_title = client.get(
        f"{TICKETS_URL}?q=billing",
        headers=auth_header(admin),
    )
    assert res_title.status_code == 200
    titles = {t["title"] for t in res_title.json()}
    assert titles == {"Billing issue", "Hardware"}


def test_search_respects_role_scope(client, db_session):
    customer_a = create_user(db_session, email="search-a@test.com", role="customer")
    customer_b = create_user(db_session, email="search-b@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer_a.id,
        title="Secret billing",
        description="private",
    )
    create_ticket(
        db_session,
        requester_id=customer_b.id,
        title="Other billing",
        description="not visible",
    )

    res = client.get(
        f"{TICKETS_URL}?q=billing",
        headers=auth_header(customer_a),
    )
    assert res.status_code == 200
    titles = {t["title"] for t in res.json()}
    assert titles == {"Secret billing"}


def test_search_sql_injection_is_safe(client, db_session):
    admin = create_user(db_session, email="sqli-admin@test.com", role="admin")
    customer = create_user(db_session, email="sqli-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Normal ticket",
        description="nothing special",
    )

    res = client.get(
        f"{TICKETS_URL}?q=%25%27%3B+DROP+TABLE+tickets%3B+--",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    assert res.json() == []


def test_combined_filters(client, db_session):
    admin = create_user(db_session, email="combo-admin@test.com", role="admin")
    customer = create_user(db_session, email="combo-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Open billing",
        description="invoice",
        status="open",
        priority="high",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Closed billing",
        description="invoice",
        status="closed",
        priority="high",
    )

    res = client.get(
        f"{TICKETS_URL}?status=open&priority=high&q=billing",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    titles = {t["title"] for t in res.json()}
    assert titles == {"Open billing"}


def test_invalid_status_returns_422(client, db_session):
    admin = create_user(db_session, email="422-admin@test.com", role="admin")
    res = client.get(
        f"{TICKETS_URL}?status=invalid",
        headers=auth_header(admin),
    )
    assert res.status_code == 422


def test_invalid_priority_returns_422(client, db_session):
    admin = create_user(db_session, email="422-pri-admin@test.com", role="admin")
    res = client.get(
        f"{TICKETS_URL}?priority=invalid",
        headers=auth_header(admin),
    )
    assert res.status_code == 422


def test_assignee_id_and_unassigned_mutually_exclusive(client, db_session):
    admin = create_user(db_session, email="mutex-admin@test.com", role="admin")
    agent = create_user(db_session, email="mutex-agent@test.com", role="agent")
    res = client.get(
        f"{TICKETS_URL}?assignee_id={agent.id}&unassigned=true",
        headers=auth_header(admin),
    )
    assert res.status_code == 422
