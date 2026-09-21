from datetime import timedelta

from app.models import (
    Allocation,
    AllocationStatus,
    Resource,
    ResourceRequest,
)


class AllocationError(Exception):
    """Raised when a resource allocation cannot be completed."""
    pass


def find_conflicts(
    session,
    resource_id,
    start,
    end,
    exclude_alloc_id=None,
):
    """
    Find active allocations that overlap with the requested
    time period, including the resource's buffer time.

    Buffer is calculated in Python before building the query.
    This avoids SQLite DateTime + timedelta issues.
    """

    resource = session.get(
        Resource,
        resource_id
    )

    if resource is None:
        return []

    buffer = timedelta(
        minutes=resource.buffer_minutes or 0
    )

    # Expand the requested period by the resource buffer.
    buffered_start = start - buffer
    buffered_end = end + buffer

    query = session.query(
        Allocation
    ).filter(
        Allocation.resource_id == resource_id,

        Allocation.status.in_(
            [
                AllocationStatus.ALLOCATED,
                AllocationStatus.APPROVED,
            ]
        ),

        Allocation.start_dt < buffered_end,

        Allocation.end_dt > buffered_start,
    )

    if exclude_alloc_id is not None:

        query = query.filter(
            Allocation.id != exclude_alloc_id
        )

    return query.all()


def pick_resources(
    session,
    request_item,
    request,
):
    """
    Find suitable and available resources for a request item.
    """

    required_quantity = request_item.quantity

    # --------------------------------------------------
    # Specific resource requested
    # --------------------------------------------------

    if request_item.specific_resource_id is not None:

        resource = session.get(
            Resource,
            request_item.specific_resource_id,
        )

        if resource is None:
            raise AllocationError(
                "Requested resource does not exist."
            )

        if not resource.is_active:
            raise AllocationError(
                f"{resource.name} is not active."
            )

        if resource.type != request_item.resource_type:
            raise AllocationError(
                f"{resource.name} has the wrong resource type."
            )

        conflicts = find_conflicts(
            session,
            resource.id,
            request.requested_start,
            request.requested_end,
        )

        if conflicts:

            raise AllocationError(
                f"{resource.name} is already booked "
                f"or is within its required buffer period."
            )

        return [resource]

    # --------------------------------------------------
    # Automatically select suitable resources
    # --------------------------------------------------

    resources = (
        session.query(Resource)
        .filter(
            Resource.type == request_item.resource_type,
            Resource.is_active.is_(True),
        )
        .all()
    )

    selected_resources = []

    for resource in resources:

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

        if len(selected_resources) == required_quantity:
            break

    # --------------------------------------------------
    # Not enough resources
    # --------------------------------------------------

    if len(selected_resources) < required_quantity:

        raise AllocationError(
            (
                f"Could not allocate {required_quantity} "
                f"resource(s) of type "
                f"{request_item.resource_type.value}."
            )
        )

    return selected_resources


def allocate_request(
    session,
    request,
):
    """
    Atomically allocate all resources required by a request.

    All resources are validated before any Allocation rows
    are created.

    If any resource cannot be allocated, everything is
    rolled back.
    """

    # --------------------------------------------------
    # Get the actual SQLAlchemy Session
    # --------------------------------------------------

    if hasattr(session, "in_transaction"):
        actual_session = session
    else:
        actual_session = session()

    # --------------------------------------------------
    # Save request information before transaction work
    # --------------------------------------------------

    request_id = request.id
    event_id = request.event_id
    requested_start = request.requested_start
    requested_end = request.requested_end

    try:

        # --------------------------------------------------
        # Flush pending ORM changes
        # --------------------------------------------------

        actual_session.flush()

        # --------------------------------------------------
        # Start SQLite write transaction when necessary
        # --------------------------------------------------

        if not actual_session.in_transaction():

            connection = actual_session.connection()

            connection.exec_driver_sql(
                "BEGIN IMMEDIATE"
            )

        # --------------------------------------------------
        # Reload request from database
        # --------------------------------------------------

        db_request = (
            actual_session.query(
                ResourceRequest
            )
            .filter(
                ResourceRequest.id == request_id
            )
            .first()
        )

        if db_request is None:

            raise AllocationError(
                "Resource request does not exist."
            )

        # --------------------------------------------------
        # Get request items
        # --------------------------------------------------

        request_items = list(
            db_request.items
        )

        if not request_items:

            raise AllocationError(
                "Resource request contains no items."
            )

        # --------------------------------------------------
        # Validate ALL resources first
        # --------------------------------------------------

        planned_resources = []

        for request_item in request_items:

            resources = pick_resources(
                actual_session,
                request_item,
                db_request,
            )

            for resource in resources:

                planned_resources.append(
                    (
                        resource,
                        request_item,
                    )
                )

        # --------------------------------------------------
        # Create allocations only after validation succeeds
        # --------------------------------------------------

        allocations = []

        for resource, request_item in planned_resources:

            allocation = Allocation(
                resource_id=resource.id,
                event_id=event_id,
                request_id=request_id,
                start_dt=requested_start,
                end_dt=requested_end,
                status=AllocationStatus.ALLOCATED,
            )

            actual_session.add(
                allocation
            )

            allocations.append(
                allocation
            )

        # --------------------------------------------------
        # Commit everything atomically
        # --------------------------------------------------

        actual_session.commit()

        return allocations

    except AllocationError:

        actual_session.rollback()

        raise

    except Exception:

        actual_session.rollback()

        raise