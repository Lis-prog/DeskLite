"""
Dev seed script — creates demo users and tickets.
Run once inside the backend container:

  docker compose exec backend python seed.py

Credentials are printed at the end.
Safe to re-run: existing emails / ticket titles are skipped.
Resolved/closed tickets missing ``resolved_at`` are backfilled on each run.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.ticket import Ticket
from app.models.user import User

SEED_USERS = [
    {
        "full_name": "Alice Admin",
        "email": "admin@desklite.dev",
        "password": "Admin1234!",
        "role": "admin",
    },
    {
        "full_name": "Agent Bob",
        "email": "agent@desklite.dev",
        "password": "Agent1234!",
        "role": "agent",
    },
    {
        "full_name": "Agent Sara",
        "email": "agent2@desklite.dev",
        "password": "Agent1234!",
        "role": "agent",
    },
    {
        "full_name": "Carol Customer",
        "email": "customer@desklite.dev",
        "password": "Customer1234!",
        "role": "customer",
    },
    {
        "full_name": "Dan Developer",
        "email": "customer2@desklite.dev",
        "password": "Customer1234!",
        "role": "customer",
    },
    {
    "full_name": "Valza Dalipi",
    "email": "valza@desklite.online",
    "password": "Agent1234!",
    "role": "agent",
    },
    {
    "full_name": "Lis Pruthi",
    "email": "lis@desklite.online",
    "password": "Admin1234!",
    "role": "admin",
    },
    {
    "full_name": "Paulina Delija",
    "email": "paulina@desklite.online",
    "password": "Admin1234!",
    "role": "admin",
    },
    {
    "full_name": "Rrezart Buzuku",
    "email": "rrezart@desklite.online",
    "password": "Admin1234!",
    "role": "admin",
    },
    {
    "full_name": "Egzona Haskuka",
    "email": "egzona@desklite.online",
    "password": "Customer1234!",
    "role": "customer",
    },

]

def _ago(days: int = 0, hours: int = 0) -> datetime:
    return datetime.now(UTC) - timedelta(days=days, hours=hours)


def _resolved_at_for_seed(status: str, created_at: datetime) -> datetime | None:
    """Demo tickets past in_progress should carry a plausible resolution time."""
    if status in ("resolved", "closed"):
        return created_at + timedelta(days=1)
    return None


def seed() -> None:
    db = SessionLocal()
    try:
        # ── Users ────────────────────────────────────────────────────────────
        created_users: list[dict] = []
        skipped_users: list[str] = []
        user_map: dict[str, User] = {}

        for u in SEED_USERS:
            existing = db.scalar(select(User).where(User.email == u["email"]))
            if existing is not None:
                skipped_users.append(u["email"])
                user_map[u["email"]] = existing
                continue

            user = User(
                email=u["email"],
                password_hash=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
            )
            db.add(user)
            db.flush()  # get auto-generated id before commit
            user_map[u["email"]] = user
            created_users.append(u)

        db.commit()
        # Re-bind after commit so IDs are stable
        for email in list(user_map):
            user_map[email] = db.scalar(select(User).where(User.email == email))  # type: ignore[assignment]

        agent1  = user_map["agent@desklite.dev"]
        agent2  = user_map["agent2@desklite.dev"]
        carol   = user_map["customer@desklite.dev"]
        dan     = user_map["customer2@desklite.dev"]

        # ── Tickets ──────────────────────────────────────────────────────────
        SEED_TICKETS = [
            # open — unassigned
            dict(
                title="Cannot log in to the portal",
                description="I get 401 every time I try to log in after the password reset.",
                status="open", priority="urgent",
                requester=carol, assignee=None, created_at=_ago(days=1),
            ),
            dict(
                title="Invoice PDF is blank",
                description="When I download the May invoice it opens as a blank PDF.",
                status="open", priority="high",
                requester=dan, assignee=None, created_at=_ago(days=2),
            ),
            dict(
                title="Add dark mode to the dashboard",
                description=(
                    "Feature request: a dark mode toggle would be great "
                    "for late-night work."
                ),
                status="open", priority="low",
                requester=carol, assignee=None, created_at=_ago(days=3),
            ),
            dict(
                title="Bulk export tickets to CSV",
                description="We need a way to export the full ticket list for reporting.",
                status="open", priority="medium",
                requester=dan, assignee=None, created_at=_ago(days=4),
            ),
            # in_progress — assigned
            dict(
                title="Email notifications not arriving",
                description="Ticket update emails stopped arriving about 3 days ago.",
                status="in_progress", priority="high",
                requester=carol, assignee=agent1, created_at=_ago(days=5),
            ),
            dict(
                title="Search returns wrong results",
                description="Searching for 'billing' returns unrelated tickets.",
                status="in_progress", priority="medium",
                requester=dan, assignee=agent1, created_at=_ago(days=6),
            ),
            dict(
                title="Attachment upload fails for PDFs",
                description="Images upload fine but PDFs always return a 500 error.",
                status="in_progress", priority="urgent",
                requester=carol, assignee=agent2, created_at=_ago(days=7),
            ),
            dict(
                title="User profile page throws 404",
                description="Navigating to /profile after login shows a 404.",
                status="in_progress", priority="high",
                requester=dan, assignee=agent2, created_at=_ago(days=8),
            ),
            # resolved
            dict(
                title="Cannot assign tickets to myself",
                description="The assign-to-me button does nothing when clicked.",
                status="resolved", priority="medium",
                requester=carol, assignee=agent1, created_at=_ago(days=10),
            ),
            dict(
                title="Priority badge shows wrong colour",
                description="High-priority tickets show the medium colour in the list view.",
                status="resolved", priority="low",
                requester=dan, assignee=agent2, created_at=_ago(days=12),
            ),
            dict(
                title="Pagination broken on ticket list",
                description="Clicking page 2 reloads page 1 instead.",
                status="resolved", priority="medium",
                requester=carol, assignee=agent1, created_at=_ago(days=14),
            ),
            # closed
            dict(
                title="Dashboard loads slowly",
                description="The admin dashboard takes 8+ seconds on first load.",
                status="closed", priority="high",
                requester=dan, assignee=agent2, created_at=_ago(days=20),
            ),
            dict(
                title="Typo in registration success msg",
                description="'Regstration successful' — missing an 'i'.",
                status="closed", priority="low",
                requester=carol, assignee=agent1, created_at=_ago(days=25),
            ),
            dict(
                title="Filter resets on page refresh",
                description="Status filter selection is lost every time the page is refreshed.",
                status="closed", priority="medium",
                requester=dan, assignee=agent2, created_at=_ago(days=30),
            ),
        ]

        created_tickets = 0
        skipped_tickets = 0

        for t in SEED_TICKETS:
            exists = db.scalar(
                select(Ticket).where(
                    Ticket.title == t["title"],
                    Ticket.requester_id == t["requester"].id,
                )
            )
            if exists is not None:
                skipped_tickets += 1
                continue

            created_at = t["created_at"]
            ticket = Ticket(
                title=t["title"],
                description=t["description"],
                status=t["status"],
                priority=t["priority"],
                requester_id=t["requester"].id,
                assignee_id=t["assignee"].id if t["assignee"] else None,
                created_at=created_at,
                resolved_at=_resolved_at_for_seed(t["status"], created_at),
            )
            db.add(ticket)
            created_tickets += 1

        backfilled = 0
        for ticket in db.scalars(
            select(Ticket).where(
                Ticket.status.in_(("resolved", "closed")),
                Ticket.resolved_at.is_(None),
            )
        ):
            ticket.resolved_at = ticket.updated_at or (
                ticket.created_at + timedelta(days=1)
            )
            backfilled += 1

        # Demo satisfaction ratings on closed tickets (for presentation).
        SEED_SATISFACTION: dict[str, int] = {
            "Dashboard loads slowly": 4,
            "Typo in registration success msg": 5,
            "Filter resets on page refresh": 3,
        }
        satisfaction_created = 0
        for title, rating in SEED_SATISFACTION.items():
            ticket = db.scalar(select(Ticket).where(Ticket.title == title))
            if ticket is None or ticket.status != "closed":
                continue
            existing = db.scalar(
                select(AuditLog).where(
                    AuditLog.ticket_id == ticket.id,
                    AuditLog.action == "satisfaction_rating",
                )
            )
            if existing is not None:
                continue
            db.add(
                AuditLog(
                    actor_id=ticket.requester_id,
                    ticket_id=ticket.id,
                    action="satisfaction_rating",
                    from_value=None,
                    to_value=str(rating),
                )
            )
            satisfaction_created += 1

        db.commit()

        # ── Report ───────────────────────────────────────────────────────────
        print("\n── DeskLite seed ──────────────────────────────────────────")
        if created_users:
            print(f"\n{'Role':<12} {'Email':<32} {'Password'}")
            print("─" * 62)
            for u in created_users:
                print(f"{u['role']:<12} {u['email']:<32} {u['password']}")
        if skipped_users:
            print(f"\nUsers skipped (already exist): {', '.join(skipped_users)}")

        print(
            f"\nTickets created: {created_tickets}  |  skipped: {skipped_tickets}"
            f"  |  resolved_at backfilled: {backfilled}"
            f"  |  satisfaction ratings: {satisfaction_created}"
        )
        print("───────────────────────────────────────────────────────────\n")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
