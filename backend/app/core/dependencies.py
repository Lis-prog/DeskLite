from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db


class _UserStub:
    """Temporary stand-in until app.models.user.User exists."""

    def __init__(self, id: int, role: str, email: str):
        self.id = id
        self.role = role
        self.email = email


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> _UserStub:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    access_token = request.cookies.get("access_token")
    if access_token is None:
        raise credentials_exc from None

    try:
        payload = decode_token(access_token, expected_type="access")
        user_id = payload["sub"]
        role = payload["role"]
        email = payload.get("email") or ""
    except ValueError:
        raise credentials_exc from None

    return _UserStub(id=int(user_id), role=role, email=email)


def require_roles(*roles: str):
    def _check(user: _UserStub = Depends(get_current_user)) -> _UserStub:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return user
    return _check