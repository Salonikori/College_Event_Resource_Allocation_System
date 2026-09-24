from datetime import timedelta

from app.models import (
    Allocation,
    AllocationStatus,
    EventStatus,
    Resource,
    ResourceRequest,
    RequestStatus,
)

from app.services.suitability import check_suitability


# ============================================================
# EXCEPTION
# ============================================================

class AllocationError(Exception):
    """Raised when a resource allocation cannot be completed."""

    pass


# ============================================================
# SUITABILITY ERROR
# ============================================================

def _format_suitability_error(
    resource,
    reasons,
):
    """
    Convert suitability reason tuples into one clear
    allocation error message.
    """

    if not reasons:
        return None

    details = "; ".join(
        message
        for _, message in reasons
    )

    return (
        f"{resource.name} cannot be allocated. "
        f"Reason: {details}."
    )


# ============================================================
# FIND CONFLICTS
# ============================================================

def find_conflicts(
    session,
    resource_id,
    start,
    end,
    exclude_alloc_id=None,
):
    """
    Find active allocations that overlap the requested
    time period, including buffer time.

    CANCELLED allocations are intentionally excluded.
    Therefore a cancelled allocation does not block
    future bookings.
    """

    resource = session.get(
        Resource,
        resource_id,
    )

    if resource is None:
        return []

    buffer = timedelta(
        minutes=resource.buffer_minutes or 0
    )

    buffered_start = (
        start - buffer
    )

    buffered_end = (
        end + buffer
    )

    query = (
        session.query(
            Allocation
        )
        .filter(
            Allocation.resource_id
            == resource_id,

            Allocation.status.in_(
                [
                    AllocationStatus.ALLOCATED,
                    AllocationStatus.APPROVED,
                ]
            ),

            Allocation.start_dt
            < buffered_end,

            Allocation.end_dt
            > buffered_start,
        )
    )

    if exclude_alloc_id is not None:

        query = query.filter(
            Allocation.id
            != exclude_alloc_id
        )

    return query.all()


# ============================================================
# VALIDATE REQUEST
# ============================================================

def _validate_request(
    request,
):
    """
    Validate the event, request status and requested
    time before selecting resources.
    """

    event = request.event

    # --------------------------------------------------------
    # Event existence
    # --------------------------------------------------------

    if event is None:

        raise AllocationError(
            "The event associated with this request "
            "does not exist."
        )

    # --------------------------------------------------------
    # Event status
    # --------------------------------------------------------

    if event.status == EventStatus.CANCELLED:

        raise AllocationError(
            f"Event '{event.name}' is cancelled "
            "and cannot receive new allocations."
        )

    if event.status == EventStatus.REJECTED:

        raise AllocationError(
            f"Event '{event.name}' is rejected "
            "and cannot receive new allocations."
        )

    # --------------------------------------------------------
    # Request status
    # --------------------------------------------------------

    if request.status in {
        RequestStatus.REJECTED,
        RequestStatus.CANCELLED,
    }:

        raise AllocationError(
            f"Request #{request.id} is "
            f"{request.status.value.lower()} "
            "and cannot be allocated."
        )

    # --------------------------------------------------------
    # Requested time
    # --------------------------------------------------------

    if (
        request.requested_start is None
        or request.requested_end is None
    ):

        raise AllocationError(
            "Requested start and end times are required."
        )

    # --------------------------------------------------------
    # End after start
    # --------------------------------------------------------

    if (
        request.requested_end
        <= request.requested_start
    ):

        raise AllocationError(
            "Requested end time must be after "
            "requested start time."
        )

    # --------------------------------------------------------
    # Request inside event
    # --------------------------------------------------------

    if (
        request.requested_start
        < event.start_dt

        or

        request.requested_end
        > event.end_dt
    ):

        raise AllocationError(
            "Requested allocation time must fall "
            "within the event start and end time."
        )


# ============================================================
# PICK RESOURCES
# ============================================================

def pick_resources(
    session,
    request_item,
    request,
    unavailable_resource_ids=None,
):
    """
    Find suitable and available physical resources
    for one RequestItem.

    This function does not create Allocation rows.
    It only validates and selects resources.

    Checks:

    - Quantity
    - Resource type
    - Active status
    - Suitability
    - Capacity
    - Availability
    - Buffer time
    - Previously selected resources
    """

    required_quantity = (
        request_item.quantity
    )

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    if (
        required_quantity is None
        or required_quantity <= 0
    ):

        raise AllocationError(
            f"Quantity for "
            f"{request_item.resource_type.value} "
            "must be greater than zero."
        )

    unavailable_resource_ids = set(
        unavailable_resource_ids
        or set()
    )

    # ========================================================
    # SPECIFIC RESOURCE
    # ========================================================

    if (
        request_item.specific_resource_id
        is not None
    ):

        if required_quantity != 1:

            raise AllocationError(
                f"A specific "
                f"{request_item.resource_type.value} "
                "can only be requested with quantity 1."
            )

        resource = session.get(
            Resource,
            request_item.specific_resource_id,
        )

        if resource is None:

            raise AllocationError(
                "Requested resource does not exist."
            )

        if resource.id in unavailable_resource_ids:

            raise AllocationError(
                f"{resource.name} cannot be allocated. "
                "Reason: the resource is already selected."
            )

        # ----------------------------------------------------
        # Centralized suitability
        # ----------------------------------------------------

        suitability_reasons = (
            check_suitability(
                resource,
                request.event,
                request_item.resource_type,
            )
        )

        error = _format_suitability_error(
            resource,
            suitability_reasons,
        )

        if error:

            raise AllocationError(
                error
            )

        # ----------------------------------------------------
        # Conflict
        # ----------------------------------------------------

        conflicts = find_conflicts(
            session,
            resource.id,
            request.requested_start,
            request.requested_end,
        )

        if conflicts:

            raise AllocationError(
                f"{resource.name} cannot be allocated. "
                "Reason: resource is already booked or "
                "is within its required buffer period."
            )

        return [
            resource
        ]

    # ========================================================
    # AUTOMATIC RESOURCE SELECTION
    # ========================================================

    resources = (
        session.query(
            Resource
        )
        .filter(
            Resource.type
            == request_item.resource_type
        )
        .order_by(
            Resource.name.asc()
        )
        .all()
    )

    selected_resources = []

    for resource in resources:

        # ----------------------------------------------------
        # Don't reuse a resource selected by another item
        # ----------------------------------------------------

        if resource.id in unavailable_resource_ids:

            continue

        # ----------------------------------------------------
        # Suitability
        # ----------------------------------------------------

        suitability_reasons = (
            check_suitability(
                resource,
                request.event,
                request_item.resource_type,
            )
        )

        if suitability_reasons:

            continue

        # ----------------------------------------------------
        # Conflict
        # ----------------------------------------------------

        conflicts = find_conflicts(
            session,
            resource.id,
            request.requested_start,
            request.requested_end,
        )

        if conflicts:

            continue

        selected_resources.append(
            resource
        )

        if (
            len(selected_resources)
            == required_quantity
        ):

            break

    # ========================================================
    # NOT ENOUGH RESOURCES
    # ========================================================

    if (
        len(selected_resources)
        < required_quantity
    ):

        # Try to return a useful suitability reason.

        all_resources = [
            resource

            for resource in resources

            if resource.id
            not in unavailable_resource_ids
        ]

        for resource in all_resources:

            reasons = check_suitability(
                resource,
                request.event,
                request_item.resource_type,
            )

            if reasons:

                first_reason = (
                    reasons[0][1]
                )

                raise AllocationError(
                    f"{resource.name} cannot be allocated. "
                    f"Reason: {first_reason}."
                )

        raise AllocationError(
            f"Could not allocate "
            f"{required_quantity} resource(s) "
            f"of type "
            f"{request_item.resource_type.value}."
        )

    return selected_resources


# ============================================================
# ALLOCATE REQUEST
# ============================================================

def allocate_request(
    session,
    request,
    *,
    commit=True,
):
    """
    Atomically allocate ALL resources required by a request.

    Workflow:

        Start transaction
              ↓
        Validate request
              ↓
        Validate ALL request items
              ↓
        Check suitability for ALL
              ↓
        Check conflicts for ALL
              ↓
        Select ALL resources
              ↓
        Create ALL allocation rows
              ↓
        Commit
              ↓
        Success

    If ANY item fails:

        Rollback
        ↓
        ZERO allocations are created.

    Parameters
    ----------
    commit:
        True:
            allocate_request owns the transaction and commits it.

        False:
            allocations remain in the current transaction.
            The caller must commit.

            The approval workflow uses commit=False so that:

                allocations
                +
                request status APPROVED

            are committed together.
    """

    # --------------------------------------------------------
    # Get actual SQLAlchemy session
    # --------------------------------------------------------

    if hasattr(
        session,
        "in_transaction",
    ):

        actual_session = session

    else:

        actual_session = session()

    request_id = request.id

    try:

        # ----------------------------------------------------
        # Start/continue transaction
        # ----------------------------------------------------

        actual_session.flush()

        # ----------------------------------------------------
        # Reload request
        # ----------------------------------------------------

        db_request = (
            actual_session.query(
                ResourceRequest
            )
            .filter(
                ResourceRequest.id
                == request_id
            )
            .first()
        )

        if db_request is None:

            raise AllocationError(
                "Resource request does not exist."
            )

        # ----------------------------------------------------
        # Validate request
        # ----------------------------------------------------

        _validate_request(
            db_request
        )

        # ----------------------------------------------------
        # Request items
        # ----------------------------------------------------

        request_items = list(
            db_request.items
        )

        if not request_items:

            raise AllocationError(
                "Resource request contains no items."
            )

        # ====================================================
        # PHASE 1
        # Validate EVERY item first
        # ====================================================

        planned_resources = []

        planned_resource_ids = set()

        for request_item in request_items:

            selected_resources = pick_resources(
                actual_session,

                request_item,

                db_request,

                unavailable_resource_ids=
                    planned_resource_ids,
            )

            for resource in selected_resources:

                planned_resources.append(
                    (
                        resource,
                        request_item,
                    )
                )

                planned_resource_ids.add(
                    resource.id
                )

        # ====================================================
        # PHASE 2
        # Create allocations ONLY after every item passed
        # ====================================================

        allocations = []

        for (
            resource,
            request_item,
        ) in planned_resources:

            allocation = Allocation(
                resource_id=resource.id,

                event_id=db_request.event_id,

                request_id=db_request.id,

                start_dt=
                    db_request.requested_start,

                end_dt=
                    db_request.requested_end,

                status=
                    AllocationStatus.ALLOCATED,
            )

            actual_session.add(
                allocation
            )

            allocations.append(
                allocation
            )

        # ----------------------------------------------------
        # Flush allocation rows
        # ----------------------------------------------------

        actual_session.flush()

        # ----------------------------------------------------
        # Commit if this function owns the transaction
        # ----------------------------------------------------

        if commit:

            actual_session.commit()

        # Otherwise the caller commits.

        return allocations

    except AllocationError:

        actual_session.rollback()

        raise

    except Exception:

        actual_session.rollback()

        raise