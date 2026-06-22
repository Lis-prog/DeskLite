"""Access-guard tests for the admin dashboard.

The dashboard is fed by admin-only data sources (`/admin/users` and the
per-agent workload metric). These tests lock in that non-admins can never reach
that data via the API, which — together with the frontend `RequireAdmin` guard —
keeps the dashboard admin-only end to end.
"""

from __future__ import annotations

from tests.conftest import auth_header, create_user

USERS_URL = "/api/v1/admin/users"
WORKLOAD_URL = "/api/v1/metrics/agents/workload"


def test_dashboard_user_source_requires_auth(client):
    assert client.get(USERS_URL).status_code == 401


def test_dashboard_workload_source_requires_auth(client):
    assert client.get(WORKLOAD_URL).status_code == 401


def test_dashboard_sources_forbidden_for_customer(client, db_session):
    customer = create_user(db_session, email="dash-cust@test.com", role="customer")
    headers = auth_header(customer)
    assert client.get(USERS_URL, headers=headers).status_code == 403
    assert client.get(WORKLOAD_URL, headers=headers).status_code == 403


def test_dashboard_sources_forbidden_for_agent(client, db_session):
    agent = create_user(db_session, email="dash-agent@test.com", role="agent")
    headers = auth_header(agent)
    assert client.get(USERS_URL, headers=headers).status_code == 403
    assert client.get(WORKLOAD_URL, headers=headers).status_code == 403


def test_dashboard_sources_allowed_for_admin(client, db_session):
    admin = create_user(db_session, email="dash-admin@test.com", role="admin")
    headers = auth_header(admin)
    assert client.get(USERS_URL, headers=headers).status_code == 200
    assert client.get(WORKLOAD_URL, headers=headers).status_code == 200
