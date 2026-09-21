from app.models import Resource


def check_suitability(resource, event, required_type):
    """
    Check whether a resource is suitable for an event.

    Returns:
        A list of tuples containing:
        (reason_code, reason_message)

    An empty list means the resource is suitable.
    """

    reasons = []

    # --------------------------------------------------------
    # Check 1: Resource must be active
    # --------------------------------------------------------

    if not resource.is_active:
        reasons.append(
            (
                "INACTIVE",
                f"{resource.name} is deactivated"
            )
        )

    # --------------------------------------------------------
    # Check 2: Resource type must match
    # --------------------------------------------------------

    if resource.type != required_type:
        reasons.append(
            (
                "TYPE_MISMATCH",
                f"Need {required_type.value}, got {resource.type.value}"
            )
        )

    # --------------------------------------------------------
    # Check 3: Resource capacity must be sufficient
    # --------------------------------------------------------

    if (
        resource.capacity is not None
        and resource.capacity < event.expected_attendance
    ):
        reasons.append(
            (
                "INSUFFICIENT_CAPACITY",
                (
                    f"Capacity {resource.capacity} < "
                    f"{event.expected_attendance}"
                )
            )
        )

    return reasons