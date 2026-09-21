
from datetime import timedelta
from math import inf

from app.models import Resource
from app.services.booking import find_conflicts


def find_alternatives(
    session,
    event,
    required_type,
    start_dt,
    end_dt,
):
    """
    Find suitable alternative resources for an event.

    Selection criteria:
    1. Resource must be active.
    2. Resource type must match.
    3. Resource capacity must be sufficient.
    4. Resource must be available, including buffer time.
    5. Prefer the smallest suitable resource.
    6. Prefer shorter buffer times when capacity is otherwise
       equivalent.

    Returns:
        List of dictionaries containing resource, score and reason.
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

        # ---------------------------------------------------------
        # 1. Check capacity
        # ---------------------------------------------------------

        if resource.capacity is None:
            capacity = inf
        else:
            capacity = resource.capacity

        if capacity < event.expected_attendance:
            continue

        # ---------------------------------------------------------
        # 2. Check booking conflicts
        #
        # find_conflicts() already accounts for the resource's
        # buffer_minutes.
        # ---------------------------------------------------------

        conflicts = find_conflicts(
            session=session,
            resource_id=resource.id,
            start=start_dt,
            end=end_dt,
        )

        if conflicts:
            continue

        # ---------------------------------------------------------
        # 3. Calculate best-fit score
        # ---------------------------------------------------------

        if capacity == inf:
            unused_capacity = inf
        else:
            unused_capacity = (
                capacity - event.expected_attendance
            )

        # Smaller unused capacity is preferred.
        #
        # Buffer is used as a secondary factor.
        if unused_capacity == inf:
            score = (
                inf,
                resource.buffer_minutes or 0,
            )
        else:
            score = (
                unused_capacity,
                resource.buffer_minutes or 0,
            )

        # ---------------------------------------------------------
        # 4. Build explanation
        # ---------------------------------------------------------

        if capacity == inf:
            capacity_text = "unlimited capacity"
        else:
            capacity_text = f"capacity {capacity}"

        buffer_minutes = resource.buffer_minutes or 0

        candidates.append(
            {
                "resource": resource,
                "score": score,
                "reason": (
                    f"{resource.name} is available, has "
                    f"{capacity_text}, and requires a "
                    f"{buffer_minutes}-minute buffer."
                ),
            }
        )

    # -------------------------------------------------------------
    # 5. Sort by best fit
    # -------------------------------------------------------------

    candidates.sort(
        key=lambda candidate: candidate["score"]
    )

    return candidates


def find_nearby_time_slots(
    session,
    resource,
    start_dt,
    end_dt,
    search_minutes=120,
    step_minutes=30,
):
    """
    Find nearby available time slots for a specific resource.

    The function searches both before and after the requested time.

    Example:

        Requested:
        2:00 PM - 4:00 PM

        Possible alternatives:

        1:00 PM - 3:00 PM
        3:00 PM - 5:00 PM
        4:00 PM - 6:00 PM

    Args:
        session:
            SQLAlchemy database session.

        resource:
            Resource object to check.

        start_dt:
            Requested starting datetime.

        end_dt:
            Requested ending datetime.

        search_minutes:
            How far from the requested time to search.

        step_minutes:
            Size of each time shift.

    Returns:
        List of available nearby time slots.
    """

    duration = end_dt - start_dt

    suggestions = []

    # -------------------------------------------------------------
    # Validate time range
    # -------------------------------------------------------------

    if end_dt <= start_dt:
        return suggestions

    # -------------------------------------------------------------
    # Search before and after requested time
    # -------------------------------------------------------------

    for offset in range(
        step_minutes,
        search_minutes + step_minutes,
        step_minutes,
    ):

        # =========================================================
        # OPTION 1 — Earlier time slot
        # =========================================================

        earlier_start = start_dt - timedelta(
            minutes=offset
        )

        earlier_end = earlier_start + duration

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

        # =========================================================
        # OPTION 2 — Later time slot
        # =========================================================

        later_start = start_dt + timedelta(
            minutes=offset
        )

        later_end = later_start + duration

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

    # -------------------------------------------------------------
    # Sort by closest time to requested slot
    # -------------------------------------------------------------

    suggestions.sort(
        key=lambda suggestion: suggestion["distance_minutes"]
    )

    return suggestions


def get_resource_alternatives(
    session,
    event,
    required_type,
    start_dt,
    end_dt,
    search_minutes=120,
    step_minutes=30,
):
    """
    Complete alternative-selection function.

    First:
        Try to find another suitable resource at the requested time.

    If suitable resources are available:
        Return them.

    If no resource is available:
        Find nearby time slots for suitable resources.

    Returns:
        {
            "exact_time": [...],
            "nearby_time": [...]
        }
    """

    # -------------------------------------------------------------
    # 1. Find resources available at the requested time
    # -------------------------------------------------------------

    exact_time = find_alternatives(
        session=session,
        event=event,
        required_type=required_type,
        start_dt=start_dt,
        end_dt=end_dt,
    )

    # -------------------------------------------------------------
    # 2. If resources are available, return them
    # -------------------------------------------------------------

    if exact_time:
        return {
            "exact_time": exact_time,
            "nearby_time": [],
        }

    # -------------------------------------------------------------
    # 3. No exact-time resource found.
    #
    # Find suitable resources first, ignoring their current
    # availability.
    # -------------------------------------------------------------

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

        # Check capacity
        if resource.capacity is not None:
            if resource.capacity < event.expected_attendance:
                continue

        # Find nearby free slots
        slots = find_nearby_time_slots(
            session=session,
            resource=resource,
            start_dt=start_dt,
            end_dt=end_dt,
            search_minutes=search_minutes,
            step_minutes=step_minutes,
        )

        nearby_time.extend(slots)

    # -------------------------------------------------------------
    # 4. Closest time slots first
    # -------------------------------------------------------------

    nearby_time.sort(
        key=lambda slot: slot["distance_minutes"]
    )

    return {
        "exact_time": [],
        "nearby_time": nearby_time,
    }

