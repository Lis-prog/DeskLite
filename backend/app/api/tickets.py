from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import _UserStub, get_current_user
from app.db.session import get_db
from app.models.ticket import Ticket
from app.schemas.ticket import TicketRead, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _may_modify(user: _UserStub, ticket: Ticket) -> bool:
    """Object-level authorization for mutating a ticket.

    - admin  → any ticket
    - agent  → only tickets assigned to them
    - customer → only tickets they raised
    """
    if user.role == "admin":
        return True
    if user.role == "agent":
        return ticket.assignee_id == user.id
    return ticket.requester_id == user.id


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    user: _UserStub = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Ticket:
    """Update whitelisted fields on a ticket.

    Identity comes from the JWT, never the body. Callers who are not allowed to
    see the ticket get 404 (we don't leak existence — IDOR guard, AGENTS.md §5).
    """
    ticket = db.get(Ticket, ticket_id)
    if ticket is None or not _may_modify(user, ticket):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updatable fields provided.",
        )

    for field, value in changes.items():
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)
    return ticket
