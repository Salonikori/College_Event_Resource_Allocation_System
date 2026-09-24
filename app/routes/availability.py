from datetime import datetime

from flask import (
    Blueprint,
    flash,
    render_template,
    request,
)

from app import db

from app.models import (
    Allocation,
    AllocationStatus,
    Resource,
)

from app.services.booking import find_conflicts


availability_bp = Blueprint(
    "availability",
    __name__,
    url_prefix="/availability",
)


# ============================================================
# HELPERS
# ============================================================

def _active_allocations_for_resource(
    resource_id,
):
    """
    Return current active allocations for a resource.

    Cancelled allocations are intentionally excluded because
    they must not block future bookings.
    """

    return (
        Allocation.query
        .filter(
            Allocation.resource_id == resource_id,

            Allocation.status.in_(
                [
                    AllocationStatus.ALLOCATED,
                    AllocationStatus.APPROVED,
                ]
            ),
        )
        .order_by(
            Allocation.start_dt.asc()
        )
        .all()
    )


def _form_context():
    """
    Preserve submitted availability form values.
    """

    return {
        "resource_id": request.form.get(
            "resource_id",
            "",
        ).strip(),

        "date": request.form.get(
            "date",
            "",
        ).strip(),

        "start_time": request.form.get(
            "start_time",
            "",
        ).strip(),

        "end_time": request.form.get(
            "end_time",
            "",
        ).strip(),
    }


def _render(
    resources,
    selected_resource=None,
    bookings=None,
    result=None,
    form_data=None,
    status_code=200,
):
    """
    Central rendering helper.
    """

    return render_template(
        "availability.html",

        resources=resources,

        selected_resource=
            selected_resource,

        bookings=
            bookings or [],

        result=
            result,

        form_data=
            form_data or {},
    ), status_code


# ============================================================
# AVAILABILITY
# ============================================================

@availability_bp.route(
    "/",
    methods=["GET", "POST"],
)
def availability():

    # --------------------------------------------------------
    # Show ALL resources so inactive resources are visible.
    # --------------------------------------------------------

    resources = (
        Resource.query
        .order_by(
            Resource.name.asc()
        )
        .all()
    )

    selected_resource = None
    bookings = []
    result = None

    # --------------------------------------------------------
    # GET values
    # --------------------------------------------------------

    form_data = {
        "resource_id": request.args.get(
            "resource_id",
            "",
        ).strip(),

        "date": request.args.get(
            "date",
            "",
        ).strip(),

        "start_time": request.args.get(
            "start_time",
            "",
        ).strip(),

        "end_time": request.args.get(
            "end_time",
            "",
        ).strip(),
    }

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        form_data = _form_context()

        resource_id = form_data[
            "resource_id"
        ]

        date_value = form_data[
            "date"
        ]

        start_value = form_data[
            "start_time"
        ]

        end_value = form_data[
            "end_time"
        ]

        # ----------------------------------------------------
        # Resource required
        # ----------------------------------------------------

        if not resource_id:

            flash(
                "Please select a resource.",
                "error",
            )

            return _render(
                resources,
                form_data=form_data,
            )

        # ----------------------------------------------------
        # Resource ID
        # ----------------------------------------------------

        try:

            resource_id_int = int(
                resource_id
            )

        except ValueError:

            flash(
                "Invalid resource selected.",
                "error",
            )

            return _render(
                resources,
                form_data=form_data,
            )

        # ----------------------------------------------------
        # Resource lookup
        # ----------------------------------------------------

        selected_resource = db.session.get(
            Resource,
            resource_id_int,
        )

        if selected_resource is None:

            flash(
                "Resource not found.",
                "error",
            )

            return _render(
                resources,
                form_data=form_data,
            )

        # ----------------------------------------------------
        # Current bookings are shown even when the requested
        # availability form has an error.
        # ----------------------------------------------------

        bookings = (
            _active_allocations_for_resource(
                selected_resource.id
            )
        )

        # ----------------------------------------------------
        # Required date/time
        # ----------------------------------------------------

        if (
            not date_value
            or not start_value
            or not end_value
        ):

            flash(
                "Date, start time and end time are required.",
                "error",
            )

            return _render(
                resources,
                selected_resource=
                    selected_resource,
                bookings=
                    bookings,
                form_data=
                    form_data,
            )

        # ----------------------------------------------------
        # Parse values
        # ----------------------------------------------------

        try:

            selected_date = datetime.strptime(
                date_value,
                "%Y-%m-%d",
            ).date()

            start_clock = datetime.strptime(
                start_value,
                "%H:%M",
            ).time()

            end_clock = datetime.strptime(
                end_value,
                "%H:%M",
            ).time()

        except ValueError:

            flash(
                "Please enter a valid date and time.",
                "error",
            )

            return _render(
                resources,
                selected_resource=
                    selected_resource,
                bookings=
                    bookings,
                form_data=
                    form_data,
            )

        # ----------------------------------------------------
        # Build datetime
        # ----------------------------------------------------

        start_dt = datetime.combine(
            selected_date,
            start_clock,
        )

        end_dt = datetime.combine(
            selected_date,
            end_clock,
        )

        # ----------------------------------------------------
        # End must be after start
        # ----------------------------------------------------

        if end_dt <= start_dt:

            flash(
                "End time must be after start time.",
                "error",
            )

            return _render(
                resources,
                selected_resource=
                    selected_resource,
                bookings=
                    bookings,
                form_data=
                    form_data,
            )

        # ====================================================
        # INACTIVE RESOURCE
        # ====================================================

        if not selected_resource.is_active:

            result = {
                "available": False,

                "reason":
                    "Resource is inactive and "
                    "cannot be booked.",

                "conflicts": [],

                "start_dt":
                    start_dt,

                "end_dt":
                    end_dt,
            }

        # ====================================================
        # ACTIVE RESOURCE
        # ====================================================

        else:

            conflicts = find_conflicts(
                db.session,

                selected_resource.id,

                start_dt,

                end_dt,
            )

            # ------------------------------------------------
            # BOOKED
            # ------------------------------------------------

            if conflicts:

                result = {
                    "available": False,

                    "reason": (
                        "Resource is booked or "
                        "affected by its "
                        f"{selected_resource.buffer_minutes or 0}"
                        "-minute buffer."
                    ),

                    "conflicts":
                        conflicts,

                    "start_dt":
                        start_dt,

                    "end_dt":
                        end_dt,
                }

            # ------------------------------------------------
            # AVAILABLE
            # ------------------------------------------------

            else:

                result = {
                    "available": True,

                    "reason":
                        "Resource is available "
                        "for the selected period.",

                    "conflicts": [],

                    "start_dt":
                        start_dt,

                    "end_dt":
                        end_dt,
                }

    # ========================================================
    # GET
    # ========================================================

    return _render(
        resources,

        selected_resource=
            selected_resource,

        bookings=
            bookings,

        result=
            result,

        form_data=
            form_data,
    )