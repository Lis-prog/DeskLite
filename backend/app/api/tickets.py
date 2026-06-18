from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import _UserStub, get_current_user, require_roles
from app.core.file_validation import (
    MAX_FILE_SIZE_BYTES,
    FileValidationError,
    validate_upload,
)
from app.core.permissions import ensure_ticket_access, scoped_ticket_query
from app.core.storage import (
    DOWNLOAD_URL_EXPIRY_SECONDS,
    StorageService,
    build_storage_key,
    get_storage_service,
)
from app.core.ticket_state import InvalidTransitionError, validate_transition
from app.db.session import get_db
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.comment import Comment
from app.models.ticket import Ticket
from app.schemas.attachment import AttachmentDownloadRead, AttachmentRead
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.ticket import (
    SatisfactionRatingRead,
    SatisfactionRatingSubmit,
    TicketCreate,
    TicketRead,
    TicketStatusUpdate,
    TicketUpdate,
)
from app.services.ticket_status import can_advance_status

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=list[TicketRead])
def list_tickets(
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> list[Ticket]:
    """List tickets visible to the caller. Scope is enforced in SQL per role."""
    stmt = scoped_ticket_query(current_user)
    return list(db.scalars(stmt))


# NOTE: declared before `/{ticket_id}` so the literal "queue" segment is never
# captured as a ticket id.
@router.get("/queue", response_model=list[TicketRead])
def list_agent_queue(
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(require_roles("agent")),
) -> list[Ticket]:
    """Return the calling agent's work queue: only tickets assigned to them.

    Unlike `GET /tickets` (which scopes results per role), this always filters
    strictly by `assignee_id == caller`, giving an agent a focused list of their
    own tickets. Only agents can be assignees, so the endpoint is restricted to
    the agent role; other roles receive 403.
    """
    stmt = (
        select(Ticket)
        .where(Ticket.assignee_id == current_user.id)
        .order_by(Ticket.created_at.desc())
    )
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


# ── Comments ──────────────────────────────────────────────────────────────────


@router.get("/{ticket_id}/comments", response_model=list[CommentRead])
def list_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> list[Comment]:
    """List all comments on a ticket. Enforces the same access rules as the
    ticket itself — callers who cannot see the ticket cannot see its comments."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )
    ensure_ticket_access(current_user, ticket)

    return list(
        db.scalars(
            select(Comment)
            .where(Comment.ticket_id == ticket_id)
            .options(joinedload(Comment.author))
            .order_by(Comment.created_at)
        )
    )


@router.post(
    "/{ticket_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    ticket_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> Comment:
    """Post a comment on a ticket. `author_id` comes from the JWT."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )
    ensure_ticket_access(current_user, ticket)

    comment = Comment(
        ticket_id=ticket_id,
        author_id=current_user.id,
        body=payload.body,
    )
    db.add(comment)
    db.commit()

    # Re-fetch with author joined so CommentRead can serialize author.full_name.
    return db.scalar(  # type: ignore[return-value]
        select(Comment)
        .where(Comment.id == comment.id)
        .options(joinedload(Comment.author))
    )


# ── Attachments ───────────────────────────────────────────────────────────────


async def _read_upload_with_limit(file: UploadFile) -> tuple[bytes, str, str]:
    """Read multipart body up to MAX_FILE_SIZE_BYTES + 1 to detect oversize uploads."""
    filename = file.filename or ""
    content_type = file.content_type or "application/octet-stream"
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE_BYTES:
            raise FileValidationError(
                f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
            )
        chunks.append(chunk)
    body = b"".join(chunks)
    validate_upload(filename, content_type, len(body))
    return body, filename, content_type


@router.post(
    "/{ticket_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
) -> Attachment:
    """Upload a file to object storage and persist metadata on the ticket."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )
    ensure_ticket_access(current_user, ticket)

    try:
        body, filename, content_type = await _read_upload_with_limit(file)
    except FileValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    storage_key = build_storage_key(ticket_id, filename)
    storage.upload(key=storage_key, body=body, content_type=content_type)

    attachment = Attachment(
        ticket_id=ticket_id,
        uploader_id=current_user.id,
        filename=filename,
        content_type=content_type.split(";", 1)[0].strip().lower(),
        size=len(body),
        storage_key=storage_key,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{ticket_id}/attachments", response_model=list[AttachmentRead])
def list_attachments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> list[Attachment]:
    """List attachment metadata for a ticket, oldest first.

    Enforces the same access rules as the ticket itself — callers who cannot see
    the ticket cannot see its attachments (AGENTS.md §5). Only metadata is
    returned; the binary content stays in object storage and `storage_key` is
    never exposed.
    """
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )
    ensure_ticket_access(current_user, ticket)

    return list(
        db.scalars(
            select(Attachment)
            .where(Attachment.ticket_id == ticket_id)
            .order_by(Attachment.created_at, Attachment.id)
        )
    )


@router.get(
    "/{ticket_id}/attachments/{attachment_id}/download",
    response_model=AttachmentDownloadRead,
)
def get_attachment_download_url(
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
) -> AttachmentDownloadRead:
    """Return a short-lived signed URL to download an attachment.

    RBAC and object-level authorization run first: only callers who may see the
    parent ticket can get a link (AGENTS.md §5). The attachment must belong to
    that ticket — a cross-ticket id returns 404, never another ticket's file.
    The bucket stays private; access is granted only through the signed URL.
    """
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )
    ensure_ticket_access(current_user, ticket)

    attachment = db.get(Attachment, attachment_id)
    if attachment is None or attachment.ticket_id != ticket_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found.",
        )

    url = storage.generate_download_url(
        key=attachment.storage_key,
        filename=attachment.filename,
    )
    return AttachmentDownloadRead(url=url, expires_in=DOWNLOAD_URL_EXPIRY_SECONDS)


# ── Status transition ─────────────────────────────────────────────────────────


@router.patch("/{ticket_id}/status", response_model=TicketRead)
def transition_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> Ticket:
    """Change ticket status when the move is allowed by the lifecycle graph.

    Only the assigned agent or an admin may change status. Illegal moves return
    400 via :func:`app.core.ticket_state.validate_transition`.
    """
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )
    ensure_ticket_access(current_user, ticket)

    if not can_advance_status(current_user, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned agent or an admin can change ticket status.",
        )

    try:
        validate_transition(ticket.status, payload.status)
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    ticket.status = payload.status
    db.commit()
    db.refresh(ticket)
    return ticket


# ── Update ─────────────────────────────────────────────────────────────────────


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


@router.get("/{ticket_id}/satisfaction", response_model=SatisfactionRatingRead | None)
def get_satisfaction_rating(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> SatisfactionRatingRead | None:
    """Return latest satisfaction rating for a ticket, if present."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )
    ensure_ticket_access(current_user, ticket)

    rating_log = db.scalar(
        select(AuditLog)
        .where(
            AuditLog.ticket_id == ticket_id,
            AuditLog.action == "satisfaction_rating",
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    if rating_log is None or rating_log.to_value is None:
        return None

    return SatisfactionRatingRead(
        rating=int(rating_log.to_value),
        submitted_at=rating_log.created_at,
    )


@router.post("/{ticket_id}/satisfaction", response_model=SatisfactionRatingRead)
def submit_satisfaction_rating(
    ticket_id: int,
    payload: SatisfactionRatingSubmit,
    db: Session = Depends(get_db),
    current_user: _UserStub = Depends(get_current_user),
) -> SatisfactionRatingRead:
    """Customers can submit/update feedback only after their ticket is closed."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )
    ensure_ticket_access(current_user, ticket)

    if current_user.role != "customer" or ticket.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can submit satisfaction rating.",
        )
    if ticket.status != "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Satisfaction rating is available only after ticket closure.",
        )

    existing_log = db.scalar(
        select(AuditLog)
        .where(
            AuditLog.ticket_id == ticket_id,
            AuditLog.actor_id == current_user.id,
            AuditLog.action == "satisfaction_rating",
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    rating_log = AuditLog(
        actor_id=current_user.id,
        ticket_id=ticket_id,
        action="satisfaction_rating",
        from_value=existing_log.to_value if existing_log else None,
        to_value=str(payload.rating),
    )
    db.add(rating_log)
    db.commit()
    db.refresh(rating_log)

    return SatisfactionRatingRead(
        rating=int(rating_log.to_value or payload.rating),
        submitted_at=rating_log.created_at,
    )
