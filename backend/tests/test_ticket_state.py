from __future__ import annotations

import pytest

from app.core.ticket_state import (
    ALLOWED_TRANSITIONS,
    CLOSED,
    IN_PROGRESS,
    OPEN,
    RESOLVED,
    STATUSES,
    InvalidTransitionError,
    allowed_targets,
    can_transition,
    is_valid_status,
    validate_transition,
)

# Every (current, target) pair the lifecycle graph permits.
VALID_TRANSITIONS = [
    (OPEN, IN_PROGRESS),
    (OPEN, RESOLVED),
    (OPEN, CLOSED),
    (IN_PROGRESS, OPEN),
    (IN_PROGRESS, RESOLVED),
    (IN_PROGRESS, CLOSED),
    (RESOLVED, IN_PROGRESS),
    (RESOLVED, CLOSED),
    (CLOSED, IN_PROGRESS),
]

# A representative set of moves the graph must reject.
INVALID_TRANSITIONS = [
    (RESOLVED, OPEN),
    (CLOSED, OPEN),
    (CLOSED, RESOLVED),
    (RESOLVED, RESOLVED),  # no-op
    (OPEN, OPEN),  # no-op
    (IN_PROGRESS, IN_PROGRESS),  # no-op
]


# --- can_transition -----------------------------------------------------------


@pytest.mark.parametrize(("current", "target"), VALID_TRANSITIONS)
def test_valid_transitions_are_allowed(current, target):
    assert can_transition(current, target) is True


@pytest.mark.parametrize(("current", "target"), INVALID_TRANSITIONS)
def test_invalid_transitions_are_rejected(current, target):
    assert can_transition(current, target) is False


def test_unknown_statuses_are_rejected():
    assert can_transition("banana", OPEN) is False
    assert can_transition(OPEN, "banana") is False
    assert can_transition("", "") is False


# --- validate_transition ------------------------------------------------------


@pytest.mark.parametrize(("current", "target"), VALID_TRANSITIONS)
def test_validate_allows_valid_transitions(current, target):
    # Should not raise.
    validate_transition(current, target)


@pytest.mark.parametrize(("current", "target"), INVALID_TRANSITIONS)
def test_validate_raises_on_invalid_transitions(current, target):
    with pytest.raises(InvalidTransitionError):
        validate_transition(current, target)


def test_invalid_transition_error_carries_offending_values():
    with pytest.raises(InvalidTransitionError) as exc_info:
        validate_transition(CLOSED, OPEN)
    err = exc_info.value
    assert err.current == CLOSED
    assert err.target == OPEN
    assert CLOSED in str(err)
    assert OPEN in str(err)


def test_invalid_transition_error_is_a_value_error():
    # Lets the endpoint layer catch it generically if it prefers.
    assert issubclass(InvalidTransitionError, ValueError)


# --- helpers ------------------------------------------------------------------


def test_is_valid_status():
    for status in STATUSES:
        assert is_valid_status(status) is True
    assert is_valid_status("banana") is False


def test_allowed_targets_matches_graph():
    assert allowed_targets(OPEN) == ALLOWED_TRANSITIONS[OPEN]
    assert allowed_targets("banana") == frozenset()


# --- graph consistency --------------------------------------------------------


def test_graph_covers_every_status():
    assert set(ALLOWED_TRANSITIONS) == set(STATUSES)


def test_graph_targets_are_known_statuses():
    for targets in ALLOWED_TRANSITIONS.values():
        assert targets <= set(STATUSES)


def test_no_status_transitions_to_itself():
    for current, targets in ALLOWED_TRANSITIONS.items():
        assert current not in targets
