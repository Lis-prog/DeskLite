"""Add indexes on tickets.status and tickets.priority.

Keeps list/search/filter queries fast as the ticket table grows: status and
priority are common filter and sort columns (see services/ticket_query.py).
assignee_id is already indexed by the initial migration.
"""

from __future__ import annotations

from alembic import op

# Keep ids short: alembic_version.version_num is VARCHAR(32).
revision = "002_ticket_indexes"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
