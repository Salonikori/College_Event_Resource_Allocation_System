from datetime import datetime

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
    Resource,
    ResourceType,
)
from app.services.booking import find_conflicts


resources_bp = Blueprint(
    "resources",
    __name__,
    url_prefix="/resources",
)


# ============================================================
# RESOURCE FORM VALIDATION
# ============================================================

def parse_resource_form():
    """
    Validate resource form data.

    Returns:
        (data, error)

    data:
        Dictionary containing validated values.

    error:
        Error message string or None.
    """

    name = request.form.get(
        "name",
        "",
    ).strip()

    resource_type = request.form.get(
        "type",
        "",
    ).strip()

    capacity = request.form.get(
        "capacity",
        "",
    ).strip()

    buffer_minutes = request.form.get(
        "buffer_minutes",
        "0",
    ).strip()

    # --------------------------------------------------------
    # Name
    # --------------------------------------------------------

    if not name:

        return None, "Resource name is required."

    # --------------------------------------------------------
    # Resource type
    # --------------------------------------------------------

    if not resource_type:

        return None, "Resource type is required."

    try:

        resource_type_enum = ResourceType(
            resource_type
        )

    except ValueError:

        return None, "Invalid resource type selected."

    # --------------------------------------------------------
    # Capacity
    # --------------------------------------------------------

    if capacity:

        try:

            capacity_value = int(
                capacity
            )

        except ValueError:

            return None, (
                "Capacity must be a valid number."
            )

        if capacity_value < 0:

            return None, (
                "Capacity cannot be negative."
            )

    else:

        capacity_value = None

    # --------------------------------------------------------
    # Buffer time
    # --------------------------------------------------------

    if buffer_minutes:

        try:

            buffer_value = int(
                buffer_minutes
            )

        except ValueError:

            return None, (
                "Buffer time must be a valid number."
            )

        if buffer_value < 0:

            return None, (
                "Buffer time cannot be negative."
            )

    else:

        buffer_value = 0

    return {
        "name": name,
        "type": resource_type_enum,
        "capacity": capacity_value,
        "buffer_minutes": buffer_value,
    }, None


# ============================================================
# LIST RESOURCES
# ============================================================

@resources_bp.route("/")
def resources():

    resources = (
        Resource.query
        .order_by(
            Resource.name.asc()
        )
        .all()
    )

    return render_template(
        "resources.html",
        resources=resources,
        resource_types=ResourceType,
    )


# ============================================================
# CREATE RESOURCE
# ============================================================

@resources_bp.route(
    "/create",
    methods=["GET", "POST"],
)
def create_resource():

    if request.method == "POST":

        data, error = parse_resource_form()

        if error:

            flash(
                error,
                "error",
            )

            return render_template(
                "resource_form.html",
                resource_types=ResourceType,
                form_data=request.form,
            )

        resource = Resource(
            name=data["name"],
            type=data["type"],
            capacity=data["capacity"],
            is_active=True,
            buffer_minutes=data["buffer_minutes"],
        )

        db.session.add(resource)
        db.session.commit()

        flash(
            "Resource created successfully.",
            "success",
        )

        return redirect(
            url_for(
                "resources.resources"
            )
        )

    return render_template(
        "resource_form.html",
        resource_types=ResourceType,
        form_data={},
    )


# ============================================================
# EDIT EXISTING RESOURCE
#
# IMPORTANT:
# This does NOT create a new Resource.
# It updates the existing database row.
# ============================================================

@resources_bp.route(
    "/<int:resource_id>/edit",
    methods=["POST"],
)
def edit_resource(resource_id):

    resource = db.session.get(
        Resource,
        resource_id,
    )

    # --------------------------------------------------------
    # Resource not found
    # --------------------------------------------------------

    if resource is None:

        flash(
            "Resource not found.",
            "error",
        )

        return redirect(
            url_for(
                "resources.resources"
            )
        )

    # --------------------------------------------------------
    # Validate submitted data
    # --------------------------------------------------------

    data, error = parse_resource_form()

    if error:

        flash(
            error,
            "error",
        )

        return redirect(
            url_for(
                "resources.resources"
            )
        )

    # --------------------------------------------------------
    # UPDATE EXISTING RESOURCE
    # --------------------------------------------------------

    resource.name = data["name"]

    resource.type = data["type"]

    resource.capacity = data["capacity"]

    resource.buffer_minutes = (
        data["buffer_minutes"]
    )

    # IMPORTANT:
    #
    # We do NOT write:
    #
    # resource = Resource(...)
    #
    # We modify the existing object.

    db.session.commit()

    flash(
        f"{resource.name} updated successfully.",
        "success",
    )

    return redirect(
        url_for(
            "resources.resources"
        )
    )


# ============================================================
# ACTIVATE RESOURCE
# ============================================================

@resources_bp.route(
    "/<int:resource_id>/activate",
    methods=["POST"],
)
def activate_resource(resource_id):

    resource = db.session.get(
        Resource,
        resource_id,
    )

    if resource is None:

        flash(
            "Resource not found.",
            "error",
        )

        return redirect(
            url_for(
                "resources.resources"
            )
        )

    if resource.is_active:

        flash(
            f"{resource.name} is already active.",
            "info",
        )

        return redirect(
            url_for(
                "resources.resources"
            )
        )

    resource.is_active = True

    db.session.commit()

    flash(
        f"{resource.name} has been activated.",
        "success",
    )

    return redirect(
        url_for(
            "resources.resources"
        )
    )


# ============================================================
# DEACTIVATE RESOURCE
# ============================================================

@resources_bp.route(
    "/<int:resource_id>/deactivate",
    methods=["POST"],
)
def deactivate_resource(resource_id):

    resource = db.session.get(
        Resource,
        resource_id,
    )

    if resource is None:

        flash(
            "Resource not found.",
            "error",
        )

        return redirect(
            url_for(
                "resources.resources"
            )
        )

    if not resource.is_active:

        flash(
            f"{resource.name} is already inactive.",
            "info",
        )

        return redirect(
            url_for(
                "resources.resources"
            )
        )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # We do NOT delete existing allocations.
    #
    # Deactivation only prevents the resource from being
    # used for NEW allocations.
    # --------------------------------------------------------

    resource.is_active = False

    db.session.commit()

    flash(
        (
            f"{resource.name} has been deactivated. "
            "It cannot be used for new allocations."
        ),
        "success",
    )

    return redirect(
        url_for(
            "resources.resources"
        )
    )


# ============================================================
# RESOURCE AVAILABILITY TIMELINE
# ============================================================

@resources_bp.route(
    "/availability"
)
def availability():

    resources = (
        Resource.query
        .order_by(
            Resource.name.asc()
        )
        .all()
    )

    # --------------------------------------------------------
    # Only active allocations are shown.
    # Cancelled allocations are excluded.
    # --------------------------------------------------------

    allocations = (
        Allocation.query
        .filter(
            Allocation.status.in_(
                [
                    AllocationStatus.ALLOCATED,
                    AllocationStatus.APPROVED,
                ]
            )
        )
        .order_by(
            Allocation.start_dt.asc()
        )
        .all()
    )

    return render_template(
        "availability.html",
        resources=resources,
        allocations=allocations,
    )


# ============================================================
# CHECK RESOURCE AVAILABILITY
# ============================================================

@resources_bp.route(
    "/availability/check",
    methods=["GET", "POST"],
)
def check_availability():

    resources = (
        Resource.query
        .filter(
            Resource.is_active.is_(True)
        )
        .order_by(
            Resource.name.asc()
        )
        .all()
    )

    availability_results = []

    if request.method == "POST":

        resource_type = request.form.get(
            "resource_type",
            "",
        ).strip()

        start_value = request.form.get(
            "start_dt",
            "",
        ).strip()

        end_value = request.form.get(
            "end_dt",
            "",
        ).strip()

        attendance = request.form.get(
            "attendance",
            "",
        ).strip()

        # ----------------------------------------------------
        # Resource type
        # ----------------------------------------------------

        if not resource_type:

            flash(
                "Please select a resource type.",
                "error",
            )

            return render_template(
                "availability_check.html",
                resources=resources,
                resource_types=ResourceType,
                availability_results=[],
            )

        try:

            resource_type_enum = ResourceType(
                resource_type
            )

        except ValueError:

            flash(
                "Invalid resource type selected.",
                "error",
            )

            return render_template(
                "availability_check.html",
                resources=resources,
                resource_types=ResourceType,
                availability_results=[],
            )

        # ----------------------------------------------------
        # Date/time
        # ----------------------------------------------------

        if not start_value or not end_value:

            flash(
                "Start and end times are required.",
                "error",
            )

            return render_template(
                "availability_check.html",
                resources=resources,
                resource_types=ResourceType,
                availability_results=[],
            )

        try:

            start_dt = datetime.fromisoformat(
                start_value
            )

            end_dt = datetime.fromisoformat(
                end_value
            )

        except ValueError:

            flash(
                "Please enter valid start and end dates.",
                "error",
            )

            return render_template(
                "availability_check.html",
                resources=resources,
                resource_types=ResourceType,
                availability_results=[],
            )

        if end_dt <= start_dt:

            flash(
                "End time must be after start time.",
                "error",
            )

            return render_template(
                "availability_check.html",
                resources=resources,
                resource_types=ResourceType,
                availability_results=[],
            )

        # ----------------------------------------------------
        # Attendance
        # ----------------------------------------------------

        attendance_value = 0

        if attendance:

            try:

                attendance_value = int(
                    attendance
                )

            except ValueError:

                flash(
                    "Attendance must be a valid number.",
                    "error",
                )

                return render_template(
                    "availability_check.html",
                    resources=resources,
                    resource_types=ResourceType,
                    availability_results=[],
                )

            if attendance_value < 0:

                flash(
                    "Attendance cannot be negative.",
                    "error",
                )

                return render_template(
                    "availability_check.html",
                    resources=resources,
                    resource_types=ResourceType,
                    availability_results=[],
                )

        # ----------------------------------------------------
        # Find resources of requested type
        # ----------------------------------------------------

        matching_resources = (
            Resource.query
            .filter(
                Resource.type == resource_type_enum,
                Resource.is_active.is_(True),
            )
            .order_by(
                Resource.name.asc()
            )
            .all()
        )

        # ----------------------------------------------------
        # Check each resource
        # ----------------------------------------------------

        for resource in matching_resources:

            # ------------------------------------------------
            # Capacity check
            # ------------------------------------------------

            if (
                resource.capacity is not None
                and resource.capacity < attendance_value
            ):

                availability_results.append(
                    {
                        "resource": resource,
                        "available": False,
                        "reason": (
                            f"Capacity {resource.capacity} "
                            f"is less than requested "
                            f"attendance "
                            f"{attendance_value}."
                        ),
                        "conflicts": [],
                    }
                )

                continue

            # ------------------------------------------------
            # Booking conflict
            # ------------------------------------------------

            conflicts = find_conflicts(
                resource=resource,
                start_dt=start_dt,
                end_dt=end_dt,
                session=db.session,
            )

            if conflicts:

                availability_results.append(
                    {
                        "resource": resource,
                        "available": False,
                        "reason": (
                            "Resource is already booked "
                            "during the requested time."
                        ),
                        "conflicts": conflicts,
                    }
                )

                continue

            # ------------------------------------------------
            # Available
            # ------------------------------------------------

            availability_results.append(
                {
                    "resource": resource,
                    "available": True,
                    "reason": (
                        "Resource is available."
                    ),
                    "conflicts": [],
                }
            )

    return render_template(
        "availability_check.html",
        resources=resources,
        resource_types=ResourceType,
        availability_results=availability_results,
    )