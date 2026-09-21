from app.models import Allocation, AllocationStatus


def find_conflicts(
    session,
    resource_id,
    start,
    end,
    exclude_alloc_id=None
):
    """
    Find active allocations that overlap with
    the requested time period for a resource.

    Two time intervals overlap when:

        existing.start < new.end
        AND
        existing.end > new.start

    Example:

        Existing: 10:00 - 14:00
        New:      12:00 - 16:00

        Result: CONFLICT
    """

    query = session.query(Allocation).filter(
        Allocation.resource_id == resource_id,

        # Cancelled allocations do not block a resource
        Allocation.status.in_([
            AllocationStatus.ALLOCATED,
            AllocationStatus.APPROVED
        ]),

        # Overlap condition
        Allocation.start_dt < end,
        Allocation.end_dt > start
    )

    # When editing an existing allocation,
    # don't compare it against itself.
    if exclude_alloc_id is not None:
        query = query.filter(
            Allocation.id != exclude_alloc_id
        )

    return query.all()