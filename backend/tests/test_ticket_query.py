from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.ticket_query import escape_ilike, validate_list_filters


class _UserStub:
    def __init__(self, role: str) -> None:
        self.role = role
        self.id = 1


def test_escape_ilike_escapes_wildcards():
    assert escape_ilike("100% done") == "100\\% done"
    assert escape_ilike("user_name") == "user\\_name"
    assert escape_ilike("back\\slash") == "back\\\\slash"


def test_validate_list_filters_rejects_non_admin_assignee():
    with pytest.raises(HTTPException) as exc:
        validate_list_filters(_UserStub("agent"), assignee_id=5, unassigned=False)
    assert exc.value.status_code == 403


def test_validate_list_filters_rejects_conflicting_assignee_params():
    with pytest.raises(HTTPException) as exc:
        validate_list_filters(_UserStub("admin"), assignee_id=5, unassigned=True)
    assert exc.value.status_code == 422
