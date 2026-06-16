from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.ticket import Ticket
from app.models.user import User

# In-memory SQLite shared across the connection pool for the whole test session.
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=_engine)
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def make_token(user_id: int, role: str = "customer", email: str = "u@test.com") -> str:
    """Mint a valid access JWT for test use."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode(
        {"sub": str(user_id), "role": role, "email": email, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def make_user(db: Session, *, role: str = "customer", email: str | None = None) -> User:
    user = User(
        email=email or f"{role}-{datetime.now(UTC).timestamp()}@test.com",
        password_hash="x",
        full_name=f"Test {role}",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_ticket(
    db: Session,
    *,
    requester_id: int,
    assignee_id: int | None = None,
    title: str = "Original title",
    description: str = "Original description",
    priority: str = "medium",
    status: str = "open",
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
    db.commit()
    db.refresh(ticket)
    return ticket
