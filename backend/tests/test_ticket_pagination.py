from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.conftest import auth_header, create_ticket, create_user

TICKETS_URL = "/api/v1/tickets"


def test_pagination_returns_page_subset(client, db_session):
    admin = create_user(db_session, email="page-admin@test.com", role="admin")
    customer = create_user(db_session, email="page-cust@test.com", role="customer")
    for i in range(5):
        create_ticket(
            db_session,
            requester_id=customer.id,
            title=f"Ticket {i}",
        )

    res = client.get(
        f"{TICKETS_URL}?page=1&page_size=2",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    assert len(res.json()) == 2
    assert res.headers["X-Total-Count"] == "5"


def test_pagination_second_page(client, db_session):
    admin = create_user(db_session, email="page2-admin@test.com", role="admin")
    customer = create_user(db_session, email="page2-cust@test.com", role="customer")
    for i in range(5):
        create_ticket(
            db_session,
            requester_id=customer.id,
            title=f"Paged {i}",
        )

    res = client.get(
        f"{TICKETS_URL}?page=2&page_size=2&sort=recent&order=asc",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    assert len(res.json()) == 2
    assert res.headers["X-Total-Count"] == "5"


def test_pagination_beyond_last_page_returns_empty(client, db_session):
    admin = create_user(db_session, email="page-empty-admin@test.com", role="admin")
    customer = create_user(db_session, email="page-empty-cust@test.com", role="customer")
    create_ticket(db_session, requester_id=customer.id, title="Only one")

    res = client.get(
        f"{TICKETS_URL}?page=99&page_size=10",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    assert res.json() == []
    assert res.headers["X-Total-Count"] == "1"


def test_no_page_size_returns_all_without_total_header(client, db_session):
    admin = create_user(db_session, email="nopage-admin@test.com", role="admin")
    customer = create_user(db_session, email="nopage-cust@test.com", role="customer")
    for i in range(3):
        create_ticket(db_session, requester_id=customer.id, title=f"All {i}")

    res = client.get(TICKETS_URL, headers=auth_header(admin))
    assert res.status_code == 200
    assert len(res.json()) == 3
    assert "X-Total-Count" not in res.headers


def test_sort_by_priority_desc(client, db_session):
    admin = create_user(db_session, email="sort-pri-admin@test.com", role="admin")
    customer = create_user(db_session, email="sort-pri-cust@test.com", role="customer")
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Low",
        priority="low",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Urgent",
        priority="urgent",
    )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Medium",
        priority="medium",
    )

    res = client.get(
        f"{TICKETS_URL}?sort=priority&order=desc",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    titles = [t["title"] for t in res.json()]
    assert titles == ["Urgent", "Medium", "Low"]


def test_sort_by_recent_asc(client, db_session):
    admin = create_user(db_session, email="sort-recent-admin@test.com", role="admin")
    customer = create_user(db_session, email="sort-recent-cust@test.com", role="customer")
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i, title in enumerate(["Oldest", "Middle", "Newest"]):
        ticket = create_ticket(db_session, requester_id=customer.id, title=title)
        ticket.created_at = base + timedelta(days=i)
    db_session.flush()

    res = client.get(
        f"{TICKETS_URL}?sort=recent&order=asc",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    titles = [t["title"] for t in res.json()]
    assert titles == ["Oldest", "Middle", "Newest"]


def test_pagination_with_status_filter(client, db_session):
    admin = create_user(db_session, email="page-filter-admin@test.com", role="admin")
    customer = create_user(db_session, email="page-filter-cust@test.com", role="customer")
    for i in range(4):
        create_ticket(
            db_session,
            requester_id=customer.id,
            title=f"Open {i}",
            status="open",
        )
    create_ticket(
        db_session,
        requester_id=customer.id,
        title="Closed one",
        status="closed",
    )

    res = client.get(
        f"{TICKETS_URL}?status=open&page=1&page_size=2",
        headers=auth_header(admin),
    )
    assert res.status_code == 200
    assert len(res.json()) == 2
    assert res.headers["X-Total-Count"] == "4"
    assert all(t["status"] == "open" for t in res.json())
