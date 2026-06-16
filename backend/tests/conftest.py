from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.session import engine, get_db
from app.main import app
from app.models.ticket import Ticket
from app.models.user import User


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user(
    db: Session,
    *,
    email: str,
    password: str = "password123",
    full_name: str = "Test User",
    role: str = "customer",
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def auth_header(user: User) -> dict[str, str]:
    """Build a Cookie header carrying a valid access token for `user`,
    so authenticated/role-gated endpoints can be exercised in tests."""
    token = create_access_token(subject=user.id, role=user.role, email=user.email)
    return {"Cookie": f"access_token={token}"}


def create_ticket(
    db: Session,
    *,
    requester_id: int,
    title: str = "Test ticket",
    description: str = "",
    priority: str = "medium",
    status: str = "open",
    assignee_id: int | None = None,
) -> Ticket:
    ticket = Ticket(
        title=title,
        description=description,
        priority=priority,
        status=status,
        requester_id=requester_id,
        assignee_id=assignee_id,
    )
    db.add(ticket)
    db.flush()
    return ticket
