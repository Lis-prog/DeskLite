from __future__ import annotations

from sqlalchemy import inspect

from app.db.session import engine
from app.models.ticket import Ticket


def _indexed_single_columns(index_dicts: list[dict]) -> set[str]:
    """Return the set of columns covered by a single-column index."""
    return {
        idx["column_names"][0]
        for idx in index_dicts
        if idx.get("column_names") and len(idx["column_names"]) == 1
    }


def test_ticket_table_indexes_exist_on_filter_columns():
    """The DB must carry indexes on the common filter/sort columns so list and
    search queries stay fast as the ticket table grows (Task #55)."""
    inspector = inspect(engine)
    indexed = _indexed_single_columns(inspector.get_indexes("tickets"))

    assert "status" in indexed
    assert "priority" in indexed
    assert "assignee_id" in indexed


def test_ticket_model_declares_filter_indexes():
    """The ORM model and the DB stay in sync: status and priority are declared
    as indexed on the model (assignee_id was already indexed)."""
    indexed_columns = {
        col.name for col in Ticket.__table__.columns if col.index
    }
    assert {"status", "priority"} <= indexed_columns
