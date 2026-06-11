from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

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
