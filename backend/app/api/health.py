from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, _UserStub
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Liveness check — does not touch the database."""
    return {"status": "ok", "service": "desklite-backend"}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """Readiness check — confirms the API can reach Postgres."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return {"status": "degraded", "database": "unavailable"}


@router.get("/health/authed")
def health_authed(current_user: _UserStub = Depends(get_current_user)):
    """
    Auth smoke-test. Requires a valid JWT cookie.
    Returns the caller's id and role so you can verify the token round-trip.
    """
    return {
        "status": "ok",
        "user_id": current_user.id,
        "role": current_user.role,
    }