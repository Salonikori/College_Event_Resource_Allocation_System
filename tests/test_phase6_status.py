import pytest

from app.models import EventStatus, RequestStatus

from app.services.status import (
    EVENT_ALLOWED_TRANSITIONS,
    REQUEST_ALLOWED_TRANSITIONS,
    InvalidStatusTransition,
    get_allowed_event_statuses,
    get_allowed_request_statuses,
    is_event_transition_allowed,
    is_request_transition_allowed,
    transition_event_status,
    transition_request_status,
)


# ============================================================
# EVENT STATUS TESTS
# ============================================================


def test_event_draft_valid_transitions():
    assert is_event_transition_allowed(
        EventStatus.DRAFT,
        EventStatus.PENDING,
    )

    assert is_event_transition_allowed(
        EventStatus.DRAFT,
        EventStatus.CANCELLED,
    )


def test_event_draft_cannot_be_approved_directly():
    assert not is_event_transition_allowed(
        EventStatus.DRAFT,
        EventStatus.APPROVED,
    )


def test_event_pending_valid_transitions():
    assert is_event_transition_allowed(
        EventStatus.PENDING,
        EventStatus.APPROVED,
    )

    assert is_event_transition_allowed(
        EventStatus.PENDING,
        EventStatus.REJECTED,
    )

    assert is_event_transition_allowed(
        EventStatus.PENDING,
        EventStatus.CANCELLED,
    )


def test_event_approved_valid_transitions():
    assert is_event_transition_allowed(
        EventStatus.APPROVED,
        EventStatus.CANCELLED,
    )

    assert is_event_transition_allowed(
        EventStatus.APPROVED,
        EventStatus.COMPLETED,
    )


@pytest.mark.parametrize(
    "status",
    [
        EventStatus.REJECTED,
        EventStatus.CANCELLED,
        EventStatus.COMPLETED,
    ],
)
def test_event_terminal_states_have_no_transitions(status):
    assert get_allowed_event_statuses(status) == []


def test_invalid_event_transition_raises_exception():
    with pytest.raises(InvalidStatusTransition):
        transition_event_status(
            EventStatus.DRAFT,
            EventStatus.APPROVED,
        )


def test_valid_event_transition_returns_new_status():
    result = transition_event_status(
        EventStatus.DRAFT,
        EventStatus.PENDING,
    )

    assert result == EventStatus.PENDING


def test_get_allowed_event_statuses():
    result = get_allowed_event_statuses(
        EventStatus.PENDING
    )

    assert result == [
        EventStatus.APPROVED,
        EventStatus.CANCELLED,
        EventStatus.REJECTED,
    ]


# ============================================================
# RESOURCE REQUEST STATUS TESTS
# ============================================================


def test_request_draft_valid_transitions():
    assert is_request_transition_allowed(
        RequestStatus.DRAFT,
        RequestStatus.PENDING,
    )

    assert is_request_transition_allowed(
        RequestStatus.DRAFT,
        RequestStatus.CANCELLED,
    )


def test_request_pending_valid_transitions():
    assert is_request_transition_allowed(
        RequestStatus.PENDING,
        RequestStatus.APPROVED,
    )

    assert is_request_transition_allowed(
        RequestStatus.PENDING,
        RequestStatus.REJECTED,
    )

    assert is_request_transition_allowed(
        RequestStatus.PENDING,
        RequestStatus.CANCELLED,
    )


def test_request_approved_can_be_cancelled():
    assert is_request_transition_allowed(
        RequestStatus.APPROVED,
        RequestStatus.CANCELLED,
    )


def test_request_approved_cannot_be_completed():
    # ResourceRequest has no COMPLETED state.
    assert not is_request_transition_allowed(
        RequestStatus.APPROVED,
        "COMPLETED",
    )


def test_invalid_request_transition_raises_exception():
    with pytest.raises(InvalidStatusTransition):
        transition_request_status(
            RequestStatus.DRAFT,
            RequestStatus.APPROVED,
        )


def test_valid_request_transition_returns_new_status():
    result = transition_request_status(
        RequestStatus.DRAFT,
        RequestStatus.PENDING,
    )

    assert result == RequestStatus.PENDING


def test_get_allowed_request_statuses():
    result = get_allowed_request_statuses(
        RequestStatus.PENDING
    )

    assert result == [
        RequestStatus.APPROVED,
        RequestStatus.CANCELLED,
        RequestStatus.REJECTED,
    ]


# ============================================================
# TRANSITION MAP TESTS
# ============================================================


def test_event_transition_map_contains_all_states():
    expected_states = {
        EventStatus.DRAFT,
        EventStatus.PENDING,
        EventStatus.APPROVED,
        EventStatus.REJECTED,
        EventStatus.CANCELLED,
        EventStatus.COMPLETED,
    }

    assert set(EVENT_ALLOWED_TRANSITIONS.keys()) == expected_states


def test_request_transition_map_contains_all_states():
    expected_states = {
        RequestStatus.DRAFT,
        RequestStatus.PENDING,
        RequestStatus.APPROVED,
        RequestStatus.REJECTED,
        RequestStatus.CANCELLED,
    }

    assert set(
        REQUEST_ALLOWED_TRANSITIONS.keys()
    ) == expected_states