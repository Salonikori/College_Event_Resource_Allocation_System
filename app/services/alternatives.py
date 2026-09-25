from datetime import timedelta
from math import inf

from app.models import (
    Event,
    Resource,
)

from app.services.booking import find_conflicts

from app.services.suitability import check_suitability


# ============================================================
# FIND EXACT-TIME ALTERNATIVE RESOURCES
# ============================================================

def find_alternatives(
    session,
    event,
    required_type,
    start_dt,
    end_dt,
    excluded_resource_id=None,
):
    """
    Find suitable alternative resources for an event.

    Rules:
    - Resource must be active.
    - Resource type must match.
    - Resource capacity must be sufficient.
    - Resource must pass suitability checks.
    - Resource must be available.
    - Buffer time is respected.
    - Requested resource can be excluded.
    - Best-fit resource is returned first.
    """

    resources = (
        session.query(Resource)
        .filter(
            Resource.type == required_type,
            Resource.is_active.is_(True),
        )
        .all()
    )

    candidates = []

    for resource in resources:

        # ----------------------------------------------------
        # Exclude originally requested resource
        # ----------------------------------------------------

        if (
            excluded_resource_id is not None
            and resource.id == excluded_resource_id
        ):
            continue

        # ----------------------------------------------------
        # Suitability
        # ----------------------------------------------------

        suitability_reasons = check_suitability(
            resource=resource,
            event=event,
            required_type=required_type,
        )

        if suitability_reasons:
            continue

        # ----------------------------------------------------
        # Capacity
        # ----------------------------------------------------

        if resource.capacity is None:

            capacity = inf

        else:

            capacity = resource.capacity

        if capacity < event.expected_attendance:
            continue

        # ----------------------------------------------------
        # Availability
        # ----------------------------------------------------

        conflicts = find_conflicts(
            session=session,
            resource_id=resource.id,
            start=start_dt,
            end=end_dt,
        )

        if conflicts:
            continue

        # ----------------------------------------------------
        # Best-fit score
        # ----------------------------------------------------

        if capacity == inf:

            unused_capacity = inf

        else:

            unused_capacity = (
                capacity
                - event.expected_attendance
            )

        buffer_minutes = (
            resource.buffer_minutes or 0
        )

        score = (
            unused_capacity,
            buffer_minutes,
        )

        # ----------------------------------------------------
        # Explanation
        # ----------------------------------------------------

        if capacity == inf:

            capacity_text = "unlimited capacity"

        else:

            capacity_text = (
                f"capacity {capacity}"
            )

        reason = (
            f"{resource.name} is available at the "
            f"requested time, has {capacity_text}, "
            f"and is suitable for "
            f"{event.expected_attendance} attendees. "
            f"Buffer: {buffer_minutes} minutes."
        )

        candidates.append(
            {
                "resource": resource,
                "score": score,
                "reason": reason,
            }
        )

    # --------------------------------------------------------
    # Best fit first
    # --------------------------------------------------------

    candidates.sort(
        key=lambda candidate: candidate["score"]
    )

    return candidates


# ============================================================
# FIND EVENT FOR LEGACY NEARBY-SLOT CALLS
# ============================================================

def _find_event_for_time(
    session,
    start_dt,
    end_dt,
):
    """
    Compatibility helper.

    Older tests/callers call find_nearby_time_slots()
    without supplying an Event.

    Try to find an event covering the requested period.
    """

    event = (
        session.query(Event)
        .filter(
            Event.start_dt <= start_dt,
            Event.end_dt >= end_dt,
        )
        .order_by(
            Event.start_dt.asc()
        )
        .first()
    )

    return event


# ============================================================
# FIND NEARBY TIME SLOTS
# ============================================================

def find_nearby_time_slots(
    session,
    resource,
    start_dt,
    end_dt,
    search_minutes=120,
    step_minutes=30,
    event=None,
    required_type=None,
):
    """
    Find nearby available time slots.

    IMPORTANT:
    The original function accepted:

        session
        resource
        start_dt
        end_dt

    That API is preserved.

    Newer callers can additionally provide:

        event
        required_type

    This keeps all existing tests and application code
    compatible.
    """

    suggestions = []

    # --------------------------------------------------------
    # Validate requested period
    # --------------------------------------------------------

    if end_dt <= start_dt:
        return suggestions

    # --------------------------------------------------------
    # Resource type
    # --------------------------------------------------------

    if required_type is None:
        required_type = resource.type

    # --------------------------------------------------------
    # Event compatibility
    # --------------------------------------------------------

    if event is None:

        event = _find_event_for_time(
            session=session,
            start_dt=start_dt,
            end_dt=end_dt,
        )

    # --------------------------------------------------------
    # If an event is available, verify suitability.
    #
    # If no event can be found, retain the legacy behaviour.
    # --------------------------------------------------------

    if event is not None:

        suitability_reasons = check_suitability(
            resource=resource,
            event=event,
            required_type=required_type,
        )

        if suitability_reasons:
            return suggestions

    # --------------------------------------------------------
    # Duration must remain unchanged
    # --------------------------------------------------------

    duration = end_dt - start_dt

    # --------------------------------------------------------
    # Search before and after
    # --------------------------------------------------------

    for offset in range(
        step_minutes,
        search_minutes + step_minutes,
        step_minutes,
    ):

        # ====================================================
        # EARLIER SLOT
        # ====================================================

        earlier_start = (
            start_dt
            - timedelta(minutes=offset)
        )

        earlier_end = (
            earlier_start
            + duration
        )

        earlier_conflicts = find_conflicts(
            session=session,
            resource_id=resource.id,
            start=earlier_start,
            end=earlier_end,
        )

        if not earlier_conflicts:

            suggestions.append(
                {
                    "resource": resource,
                    "start_dt": earlier_start,
                    "end_dt": earlier_end,
                    "distance_minutes": offset,
                    "direction": "before",
                }
            )

        # ====================================================
        # LATER SLOT
        # ====================================================

        later_start = (
            start_dt
            + timedelta(minutes=offset)
        )

        later_end = (
            later_start
            + duration
        )

        later_conflicts = find_conflicts(
            session=session,
            resource_id=resource.id,
            start=later_start,
            end=later_end,
        )

        if not later_conflicts:

            suggestions.append(
                {
                    "resource": resource,
                    "start_dt": later_start,
                    "end_dt": later_end,
                    "distance_minutes": offset,
                    "direction": "after",
                }
            )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    suggestions.sort(
        key=lambda suggestion: (
            suggestion["distance_minutes"],
            0 if suggestion["direction"] == "after" else 1,
        )
    )

    return suggestions


# ============================================================
# COMPLETE ALTERNATIVE WORKFLOW
# ============================================================

def get_resource_alternatives(
    session,
    event,
    required_type,
    start_dt,
    end_dt,
    excluded_resource_id=None,
    search_minutes=120,
    step_minutes=30,
):
    """
    Find alternatives.

    First:
        Try another resource at the exact requested time.

    If none is available:
        Search nearby time slots.
    """

    # --------------------------------------------------------
    # Exact-time alternatives
    # --------------------------------------------------------

    exact_time = find_alternatives(
        session=session,
        event=event,
        required_type=required_type,
        start_dt=start_dt,
        end_dt=end_dt,
        excluded_resource_id=excluded_resource_id,
    )

    if exact_time:

        return {
            "exact_time": exact_time,
            "nearby_time": [],
        }

    # --------------------------------------------------------
    # No exact-time alternative.
    #
    # Search suitable resources for nearby slots.
    # --------------------------------------------------------

    resources = (
        session.query(Resource)
        .filter(
            Resource.type == required_type,
            Resource.is_active.is_(True),
        )
        .all()
    )

    nearby_time = []

    for resource in resources:

        # If the request explicitly named a physical resource, an
        # alternative must be a different physical resource as well as
        # a different time. This keeps the alternative page consistent:
        # "alternative" never silently means "the same resource".
        if (
            excluded_resource_id is not None
            and resource.id == excluded_resource_id
        ):
            continue

        # ----------------------------------------------------
        # Suitability
        # ----------------------------------------------------

        suitability_reasons = check_suitability(
            resource=resource,
            event=event,
            required_type=required_type,
        )

        if suitability_reasons:
            continue

        # ----------------------------------------------------
        # Find nearby slots
        # ----------------------------------------------------

        slots = find_nearby_time_slots(
            session=session,
            resource=resource,
            start_dt=start_dt,
            end_dt=end_dt,
            search_minutes=search_minutes,
            step_minutes=step_minutes,
            event=event,
            required_type=required_type,
        )

        nearby_time.extend(
            slots
        )

    # --------------------------------------------------------
    # Sort closest first
    # --------------------------------------------------------

    nearby_time.sort(
        key=lambda slot: (
            slot["distance_minutes"],
            slot["resource"].name,
        )
    )

    return {
        "exact_time": [],
        "nearby_time": nearby_time,
    }