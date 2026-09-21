
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    url_for,
)

from app import db
from app.models import (
    RequestStatus,
    ResourceRequest,
)
from app.services.booking import (
    AllocationError,
    allocate_request,
)


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/approvals"
)


# --------------------------------------------------
# View pending requests
# --------------------------------------------------
@admin_bp.route("/")
def approvals():

    pending_requests = (
        ResourceRequest.query
        .filter_by(
            status=RequestStatus.PENDING
        )
        .order_by(
            ResourceRequest.created_at.asc()
        )
        .all()
    )

    return render_template(
        "approvals.html",
        requests=pending_requests
    )


# --------------------------------------------------
# Approve request
# --------------------------------------------------
@admin_bp.route(
    "/<int:request_id>/approve",
    methods=["POST"]
)
def approve_request(request_id):

    resource_request = db.session.get(
        ResourceRequest,
        request_id
    )

    # --------------------------------------------------
    # Request not found
    # --------------------------------------------------

    if resource_request is None:

        flash(
            "Resource request not found.",
            "error"
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------
    # Only pending requests can be approved
    # --------------------------------------------------

    if resource_request.status != RequestStatus.PENDING:

        flash(
            "Only pending requests can be approved.",
            "error"
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------
    # Try to allocate requested resources
    # --------------------------------------------------

    try:

        allocations = allocate_request(
            db.session,
            resource_request
        )

    except AllocationError as error:

        # ----------------------------------------------
        # Rollback failed allocation
        # ----------------------------------------------

        db.session.rollback()

        flash(
            f"Request could not be approved: {error}",
            "error"
        )

        # ----------------------------------------------
        # Provide a direct alternative link
        # ----------------------------------------------

        flash(
            (
                "Try checking alternative resources or "
                "nearby time slots."
            ),
            "info"
        )

        return redirect(
            url_for(
                "requests.alternatives",
                request_id=resource_request.id
            )
        )

    except Exception:

        db.session.rollback()

        flash(
            (
                "An unexpected error occurred while "
                "allocating resources."
            ),
            "error"
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------
    # Allocation successful
    # --------------------------------------------------

    resource_request.status = RequestStatus.APPROVED

    db.session.commit()

    # --------------------------------------------------
    # Build allocated resource names
    # --------------------------------------------------

    resource_names = [
        allocation.resource.name
        for allocation in allocations
    ]

    if resource_names:

        allocated_text = ", ".join(
            resource_names
        )

        success_message = (
            f"Request #{resource_request.id} approved successfully. "
            f"Allocated: {allocated_text}."
        )

    else:

        success_message = (
            f"Request #{resource_request.id} approved successfully."
        )

    flash(
        success_message,
        "success"
    )

    return redirect(
        url_for("admin.approvals")
    )


# --------------------------------------------------
# Reject request
# --------------------------------------------------
@admin_bp.route(
    "/<int:request_id>/reject",
    methods=["POST"]
)
def reject_request(request_id):

    resource_request = db.session.get(
        ResourceRequest,
        request_id
    )

    # --------------------------------------------------
    # Request not found
    # --------------------------------------------------

    if resource_request is None:

        flash(
            "Resource request not found.",
            "error"
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------
    # Only pending requests can be rejected
    # --------------------------------------------------

    if resource_request.status != RequestStatus.PENDING:

        flash(
            "Only pending requests can be rejected.",
            "error"
        )

        return redirect(
            url_for("admin.approvals")
        )

    # --------------------------------------------------
    # Reject request
    # --------------------------------------------------

    resource_request.status = RequestStatus.REJECTED

    db.session.commit()

    flash(
        f"Request #{resource_request.id} rejected.",
        "success"
    )

    return redirect(
        url_for("admin.approvals")
    )
