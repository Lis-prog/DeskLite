from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import RoleUpdate, UserRead

# Every route in this router is admin-only. Declaring the guard at the router
# level means RBAC is enforced on each endpoint by construction — a new route
# added here cannot accidentally ship without a role check.
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles("admin"))],
)


@router.get("/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    """Admin overview of all users. Non-admins never reach this (403)."""
    return list(db.scalars(select(User).order_by(User.id)))


@router.patch("/users/{user_id}/role", response_model=UserRead)
def assign_role(
    user_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
) -> User:
    """Promote/demote a user (e.g. make a customer an agent). Admin-only —
    this is the single supported way a role is ever changed."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.role = payload.role
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
