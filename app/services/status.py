# app/services/status.py

from app.models import EventStatus, RequestStatus


# ============================================================
# EXCEPTION
# ============================================================

class InvalidStatusTransition(Exception):
    """Raised when an invalid status transition is requested."""

    pass


# ============================================================
# EVENT STATUS TRANSITIONS
# ============================================================

EVENT_ALLOWED_TRANSITIONS = {
    EventStatus.DRAFT: {
        EventStatus.PENDING,
        EventStatus.CANCELLED,
    },

    EventStatus.PENDING: {
        EventStatus.APPROVED,
        EventStatus.REJECTED,
        EventStatus.CANCELLED,
    },

    EventStatus.APPROVED: {
        EventStatus.CANCELLED,
        EventStatus.COMPLETED,
    },

    EventStatus.REJECTED: set(),

    EventStatus.CANCELLED: set(),

    EventStatus.COMPLETED: set(),
}


# ============================================================
# REQUEST STATUS TRANSITIONS
# ============================================================

REQUEST_ALLOWED_TRANSITIONS = {
    RequestStatus.DRAFT: {
        RequestStatus.PENDING,
        RequestStatus.CANCELLED,
    },

    RequestStatus.PENDING: {
        RequestStatus.APPROVED,
        RequestStatus.REJECTED,
        RequestStatus.CANCELLED,
    },

    RequestStatus.APPROVED: {
        RequestStatus.CANCELLED,
    },

    RequestStatus.REJECTED: set(),

    RequestStatus.CANCELLED: set(),
}


# ============================================================
# EVENT STATUS
# ============================================================

def is_event_transition_allowed(
    current_status,
    new_status,
):
    """
    Check whether an EventStatus transition is allowed.
    """

    allowed_statuses = EVENT_ALLOWED_TRANSITIONS.get(
        current_status,
        set(),
    )

    return new_status in allowed_statuses


def transition_event_status(
    current_status,
    new_status,
):
    """
    Validate and return the new EventStatus.

    Raises:
        InvalidStatusTransition:
            If the transition is not allowed.
    """

    if not is_event_transition_allowed(
        current_status,
        new_status,
    ):
        raise InvalidStatusTransition(
            f"Invalid event status transition: "
            f"{current_status.value} -> {new_status.value}"
        )

    return new_status


def get_allowed_event_statuses(
    current_status,
):
    """
    Return all valid next EventStatus values.
    """

    return sorted(
        EVENT_ALLOWED_TRANSITIONS.get(
            current_status,
            set(),
        ),
        key=lambda status: status.value,
    )


# ============================================================
# REQUEST STATUS
# ============================================================

def is_request_transition_allowed(
    current_status,
    new_status,
):
    """
    Check whether a ResourceRequest status transition
    is allowed.
    """

    allowed_statuses = REQUEST_ALLOWED_TRANSITIONS.get(
        current_status,
        set(),
    )

    return new_status in allowed_statuses


def transition_request_status(
    current_status,
    new_status,
):
    """
    Validate and return the new RequestStatus.

    Raises:
        InvalidStatusTransition:
            If the transition is not allowed.
    """

    if not is_request_transition_allowed(
        current_status,
        new_status,
    ):
        raise InvalidStatusTransition(
            f"Invalid request status transition: "
            f"{current_status.value} -> {new_status.value}"
        )

    return new_status


def get_allowed_request_statuses(
    current_status,
):
    """
    Return all valid next RequestStatus values.
    """

    return sorted(
        REQUEST_ALLOWED_TRANSITIONS.get(
            current_status,
            set(),
        ),
        key=lambda status: status.value,
    )