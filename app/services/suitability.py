from app.models import ResourceType


# ============================================================
# RESOURCE TYPES WHERE CAPACITY REPRESENTS PEOPLE
# ============================================================

CAPACITY_BASED_RESOURCE_TYPES = {
    ResourceType.HALL,
    ResourceType.CLASSROOM,
    ResourceType.LAB,
}


# ============================================================
# SUITABILITY
# ============================================================

def check_suitability(
    resource,
    event,
    required_type,
):
    """
    Check whether a resource is suitable for an event.

    Rules:

    1. Resource must be active.
    2. Resource type must match.
    3. Capacity is checked only for physical spaces where
       capacity represents the number of people that can
       occupy the resource.

    Examples:

        Hall capacity = 200
        Attendance = 100
        -> Suitable

        Hall capacity = 50
        Attendance = 100
        -> Not suitable

        Projector capacity = 1
        Attendance = 100
        -> Suitable

        Microphone capacity = 2
        Attendance = 100
        -> Suitable

    An empty list means the resource is suitable.
    """

    reasons = []

    # ========================================================
    # CHECK 1 — ACTIVE
    # ========================================================

    if not resource.is_active:

        reasons.append(
            (
                "INACTIVE",
                f"{resource.name} is inactive",
            )
        )

    # ========================================================
    # CHECK 2 — RESOURCE TYPE
    # ========================================================

    if resource.type != required_type:

        reasons.append(
            (
                "TYPE_MISMATCH",
                (
                    f"Required type "
                    f"{required_type.value}, "
                    f"but resource type is "
                    f"{resource.type.value}"
                ),
            )
        )

    # ========================================================
    # CHECK 3 — CAPACITY
    # ========================================================
    #
    # Capacity means "number of people the resource can hold"
    # only for spaces such as:
    #
    #   HALL
    #   CLASSROOM
    #   LAB
    #
    # Equipment such as:
    #
    #   PROJECTOR
    #   MICROPHONE
    #   SPEAKER
    #   COMPUTER
    #
    # uses quantity rather than event attendance capacity.
    # ========================================================

    if resource.type in CAPACITY_BASED_RESOURCE_TYPES:

        if resource.capacity is not None:

            if (
                resource.capacity
                < event.expected_attendance
            ):

                reasons.append(
                    (
                        "INSUFFICIENT_CAPACITY",
                        (
                            f"Capacity "
                            f"{resource.capacity} "
                            f"is less than required "
                            f"attendance "
                            f"{event.expected_attendance}"
                        ),
                    )
                )

    return reasons