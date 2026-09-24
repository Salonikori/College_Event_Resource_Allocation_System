from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app import db

from app.models import (
    Allocation,
    AllocationStatus,
    EventStatus,
    RequestStatus,
    ResourceRequest,
)

from app.services.booking import (
    AllocationError,
    allocate_request,
)

from app.services.status import (
    InvalidStatusTransition,
    transition_request_status,
)


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/approvals",
)


# ============================================================
# APPROVAL DASHBOARD
# ============================================================

@admin_bp.route("/")
def approvals():

    pending_requests = (
        ResourceRequest.query
        .filter(
            ResourceRequest.status
            == RequestStatus.PENDING
        )
        .order_by(
            ResourceRequest.created_at.asc()
        )
        .all()
    )

    return render_template(
        "approvals.html",
        requests=pending_requests,
    )


# ============================================================
# APPROVE REQUEST
# ============================================================

@admin_bp.route(
    "/<int:request_id>/approve",
    methods=["POST"],
)
def approve_request(request_id):

    resource_request = db.session.get(
        ResourceRequest,
        request_id,
    )

    # --------------------------------------------------------
    # Request exists
    # --------------------------------------------------------

    if resource_request is None:

        flash(
            "Resource request not found.",
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------------
    # Only pending requests
    # --------------------------------------------------------

    if (
        resource_request.status
        != RequestStatus.PENDING
    ):

        flash(
            (
                "Only pending requests can be approved. "
                f"Current status: "
                f"{resource_request.status.value}."
            ),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------------
    # Event validation
    # --------------------------------------------------------

    event = resource_request.event

    if event is None:

        flash(
            "Approval failed: the event no longer exists.",
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    if event.status == EventStatus.CANCELLED:

        flash(
            (
                f"Request #{resource_request.id} "
                "cannot be approved because its "
                "event is cancelled."
            ),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    if event.status == EventStatus.REJECTED:

        flash(
            (
                f"Request #{resource_request.id} "
                "cannot be approved because the "
                "event is rejected."
            ),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------------
    # Request time
    # --------------------------------------------------------

    if (
        resource_request.requested_start is None
        or resource_request.requested_end is None
    ):

        flash(
            (
                f"Request #{resource_request.id} "
                "has missing requested time."
            ),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    if (
        resource_request.requested_end
        <= resource_request.requested_start
    ):

        flash(
            (
                f"Request #{resource_request.id} "
                "has an invalid requested time."
            ),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    if (
        resource_request.requested_start
        < event.start_dt
    ):

        flash(
            (
                f"Request #{resource_request.id} "
                "starts before the event starts."
            ),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    if (
        resource_request.requested_end
        > event.end_dt
    ):

        flash(
            (
                f"Request #{resource_request.id} "
                "ends after the event ends."
            ),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------------
    # Request items
    # --------------------------------------------------------

    request_items = list(
        resource_request.items
    )

    if not request_items:

        flash(
            (
                f"Request #{resource_request.id} "
                "contains no resources."
            ),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------------
    # Validate quantities
    # --------------------------------------------------------

    for item in request_items:

        if (
            item.quantity is None
            or item.quantity <= 0
        ):

            flash(
                (
                    f"Request #{resource_request.id} "
                    "contains an invalid "
                    "resource quantity."
                ),
                "error",
            )

            return redirect(
                url_for("admin.approvals")
            )

    # --------------------------------------------------------
    # Clear rejection reason if present
    # --------------------------------------------------------

    if hasattr(
        resource_request,
        "rejection_reason",
    ):

        resource_request.rejection_reason = None

    # ========================================================
    # ATOMIC APPROVAL + ALLOCATION
    # ========================================================
    #
    # IMPORTANT:
    #
    # commit=False means allocate_request() does NOT commit.
    #
    # Therefore:
    #
    # Allocation rows
    #       +
    # RequestStatus.APPROVED
    #
    # are committed together.
    #
    # If anything fails:
    #
    # rollback()
    #
    # removes BOTH.
    # ========================================================

    try:

        allocations = allocate_request(
            db.session,
            resource_request,
            commit=False,
        )

        resource_request.status = (
            transition_request_status(
                resource_request.status,
                RequestStatus.APPROVED,
            )
        )

        db.session.commit()

    except AllocationError as error:

        db.session.rollback()

        flash(
            (
                f"Request #{resource_request.id} "
                f"could not be approved: {error}"
            ),
            "error",
        )

        flash(
            (
                "No resources were allocated. "
                "The request remains pending."
            ),
            "info",
        )

        return redirect(
            url_for(
                "requests.alternatives",
                request_id=resource_request.id,
            )
        )

    except InvalidStatusTransition as error:

        db.session.rollback()

        flash(
            str(error),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    except Exception:

        db.session.rollback()

        flash(
            (
                "Approval failed. "
                "No resources were allocated."
            ),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------------
    # Success
    # --------------------------------------------------------

    resource_names = [
        allocation.resource.name
        for allocation in allocations
    ]

    allocated_text = ", ".join(
        resource_names
    )

    flash(
        (
            f"Request #{resource_request.id} "
            "approved and allocated successfully. "
            f"Resources: {allocated_text}."
        ),
        "success",
    )

    return redirect(
        url_for("admin.approvals")
    )


# ============================================================
# REJECT REQUEST
# ============================================================

@admin_bp.route(
    "/<int:request_id>/reject",
    methods=["POST"],
)
def reject_request(request_id):

    resource_request = db.session.get(
        ResourceRequest,
        request_id,
    )

    if resource_request is None:

        flash(
            "Resource request not found.",
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    if (
        resource_request.status
        != RequestStatus.PENDING
    ):

        flash(
            (
                "Only pending requests can be rejected. "
                f"Current status: "
                f"{resource_request.status.value}."
            ),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    rejection_reason = request.form.get(
        "rejection_reason",
        "",
    ).strip()

    if not rejection_reason:

        flash(
            "A rejection reason is required.",
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    if len(rejection_reason) > 1000:

        flash(
            "Rejection reason must not exceed 1000 characters.",
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    try:

        resource_request.status = (
            transition_request_status(
                resource_request.status,
                RequestStatus.REJECTED,
            )
        )

        if hasattr(
            resource_request,
            "rejection_reason",
        ):

            resource_request.rejection_reason = (
                rejection_reason
            )

        db.session.commit()

    except InvalidStatusTransition as error:

        db.session.rollback()

        flash(
            str(error),
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    except Exception:

        db.session.rollback()

        flash(
            "Unable to reject the request.",
            "error",
        )

        return redirect(
            url_for("admin.approvals")
        )

    flash(
        (
            f"Request #{resource_request.id} "
            "rejected successfully."
        ),
        "success",
    )

    return redirect(
        url_for("admin.approvals")
    )


# ============================================================
# CANCEL ALLOCATION
# ============================================================

@admin_bp.route(
    "/allocations/<int:allocation_id>/cancel",
    methods=["POST"],
)
def cancel_allocation(allocation_id):
    """
    Cancel an allocation without deleting it.

    Historical allocation remains in the database.

    find_conflicts() ignores CANCELLED allocations,
    therefore the resource becomes available again.
    """

    allocation = db.session.get(
        Allocation,
        allocation_id,
    )

    # --------------------------------------------------------
    # Not found
    # --------------------------------------------------------

    if allocation is None:

        flash(
            "Allocation not found.",
            "error",
        )

        return redirect(
            url_for("requests.requests")
        )

    # --------------------------------------------------------
    # Already cancelled
    # --------------------------------------------------------

    if (
        allocation.status
        == AllocationStatus.CANCELLED
    ):

        flash(
            (
                f"Allocation #{allocation.id} "
                "is already cancelled."
            ),
            "info",
        )

        return redirect(
            url_for("requests.requests")
        )

    # --------------------------------------------------------
    # Only active allocations can be cancelled
    # --------------------------------------------------------

    if allocation.status not in {
        AllocationStatus.ALLOCATED,
        AllocationStatus.APPROVED,
    }:

        flash(
            (
                f"Allocation #{allocation.id} "
                "cannot be cancelled from status "
                f"{allocation.status.value}."
            ),
            "error",
        )

        return redirect(
            url_for("requests.requests")
        )

    # --------------------------------------------------------
    # Cancel
    # --------------------------------------------------------

    try:

        allocation.status = (
            AllocationStatus.CANCELLED
        )

        db.session.commit()

    except Exception:

        db.session.rollback()

        flash(
            "Unable to cancel the allocation.",
            "error",
        )

        return redirect(
            url_for("requests.requests")
        )

    flash(
        (
            f"Allocation #{allocation.id} "
            "cancelled successfully. "
            "The resource is now available "
            "for future bookings."
        ),
        "success",
    )

    return redirect(
        url_for("requests.requests")
    )


# ============================================================
# ALLOCATION DETAILS
# ============================================================

@admin_bp.route(
    "/<int:request_id>/allocations",
)
def request_allocations(request_id):

    resource_request = db.session.get(
        ResourceRequest,
        request_id,
    )

    if resource_request is None:

        flash(
            "Resource request not found.",
            "error",
        )

        return redirect(
            url_for("requests.requests")
        )

    allocations = (
        Allocation.query
        .filter(
            Allocation.request_id
            == request_id
        )
        .order_by(
            Allocation.start_dt.asc()
        )
        .all()
    )

    return render_template(
        "approvals.html",
        requests=[],
        selected_request=resource_request,
        allocations=allocations,
    )