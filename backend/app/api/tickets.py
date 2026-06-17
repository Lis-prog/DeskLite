from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import _UserStub, get_current_user
from app.core.permissions import ensure_ticket_access, scoped_ticket_query
from app.db.session import get_db
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketRead, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=list[TicketRead])
def list_tickets(
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> list[Ticket]:
    """List tickets visible to the caller. Scope is enforced in SQL per role."""
    stmt = scoped_ticket_query(current_user)
    return list(db.scalars(stmt))


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> Ticket:
    """Fetch one ticket. Returns 403 when the caller may not see this row."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )
    ensure_ticket_access(current_user, ticket)
    return ticket


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> Ticket:
    """Open a new ticket. `requester_id` is taken from the JWT; `status` starts
    as "open" and `assignee_id` stays unset until an agent picks it up."""
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        requester_id=current_user.id,
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> Ticket:
    """Update whitelisted fields (title/description/priority) on a ticket.

    Identity comes from the JWT, never the body. Returns 404 when the ticket
    doesn't exist and 403 when the caller may not access it (AGENTS.md §5).
    `status` is changed only via the dedicated transition endpoint, and
    `requester_id`/`assignee_id` are not accepted here (mass-assignment guard).
    """
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )
    ensure_ticket_access(current_user, ticket)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)
    return ticket
