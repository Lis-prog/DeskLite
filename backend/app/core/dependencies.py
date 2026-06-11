from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

# replace with the real User 

class _UserStub:
    """Temporary stand-in until app.models.user.User exists."""

    def __init__(self, id: int, role: str, email: str):
        self.id = id
        self.role = role
        self.email = email

# Dependency

def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> _UserStub:

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if access_token is None:
        raise credentials_exc

    try:
        payload = jwt.decode(
            access_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: int | None = payload.get("sub")
        role: str | None = payload.get("role")
        email: str | None = payload.get("email")
        if user_id is None or role is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    return _UserStub(id=int(user_id), role=role, email=email or "")


# RBAC helpers


def require_roles(*roles: str):
    def _check(user: _UserStub = Depends(get_current_user)) -> _UserStub:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return user

    return _check