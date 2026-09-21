
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
    url_prefix="/resources"
)


# --------------------------------------------------
# List all resources
# --------------------------------------------------
@resources_bp.route("/")
def resources():

    resources = (
        Resource.query
        .order_by(Resource.name.asc())
        .all()
    )

    return render_template(
        "resources.html",
        resources=resources
    )


# --------------------------------------------------
# Create a new resource
# --------------------------------------------------
@resources_bp.route(
    "/create",
    methods=["GET", "POST"]
)
def create_resource():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        resource_type = request.form.get(
            "type",
            ""
        ).strip()

        capacity = request.form.get(
            "capacity",
            ""
        ).strip()

        buffer_minutes = request.form.get(
            "buffer_minutes",
            "0"
        ).strip()

        # ------------------------------------------
        # Basic validation
        # ------------------------------------------

        if not name:

            flash(
                "Resource name is required.",
                "error"
            )

            return render_template(
                "resource_form.html",
                resource_types=ResourceType
            )

        if not resource_type:

            flash(
                "Resource type is required.",
                "error"
            )

            return render_template(
                "resource_form.html",
                resource_types=ResourceType
            )

        # ------------------------------------------
        # Validate resource type
        # ------------------------------------------

        try:

            resource_type_enum = ResourceType(
                resource_type
            )

        except ValueError:

            flash(
                "Invalid resource type selected.",
                "error"
            )

            return render_template(
                "resource_form.html",
                resource_types=ResourceType
            )

        # ------------------------------------------
        # Validate capacity
        # ------------------------------------------

        if capacity:

            try:
                capacity_value = int(capacity)

            except ValueError:

                flash(
                    "Capacity must be a valid number.",
                    "error"
                )

                return render_template(
                    "resource_form.html",
                    resource_types=ResourceType
                )

            if capacity_value < 0:

                flash(
                    "Capacity cannot be negative.",
                    "error"
                )

                return render_template(
                    "resource_form.html",
                    resource_types=ResourceType
                )

        else:

            capacity_value = None

        # ------------------------------------------
        # Validate buffer time
        # ------------------------------------------

        if buffer_minutes:

            try:
                buffer_value = int(
                    buffer_minutes
                )

            except ValueError:

                flash(
                    "Buffer time must be a valid number.",
                    "error"
                )

                return render_template(
                    "resource_form.html",
                    resource_types=ResourceType
                )

            if buffer_value < 0:

                flash(
                    "Buffer time cannot be negative.",
                    "error"
                )

                return render_template(
                    "resource_form.html",
                    resource_types=ResourceType
                )

        else:

            buffer_value = 0

        # ------------------------------------------
        # Create resource
        # ------------------------------------------

        resource = Resource(
            name=name,
            type=resource_type_enum,
            capacity=capacity_value,
            is_active=True,
            buffer_minutes=buffer_value
        )

        db.session.add(resource)
        db.session.commit()

        flash(
            "Resource created successfully.",
            "success"
        )

        return redirect(
            url_for("resources.resources")
        )

    return render_template(
        "resource_form.html",
        resource_types=ResourceType
    )


# --------------------------------------------------
# Resource availability timeline
# --------------------------------------------------
@resources_bp.route("/availability")
def availability():

    # ------------------------------------------
    # Get all resources
    # ------------------------------------------

    resources = (
        Resource.query
        .order_by(Resource.name.asc())
        .all()
    )

    # ------------------------------------------
    # Get active allocations
    #
    # Cancelled allocations are excluded.
    # ------------------------------------------

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


# --------------------------------------------------
# Check whether a specific resource is available
# --------------------------------------------------
@resources_bp.route(
    "/availability/check",
    methods=["GET", "POST"]
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
            ""
        ).strip()

        start_value = request.form.get(
            "start_dt",
            ""
        ).strip()

        end_value = request.form.get(
            "end_dt",
            ""
        ).strip()

        attendance = request.form.get(
            "attendance",
            ""
        ).strip()

        # ------------------------------------------
        # Validate resource type
        # ------------------------------------------

        if not resource_type:

            flash(
                "Please select a resource type.",
                "error"
            )

            return render_template(
                "availability_check.html",
                resources=resources,
                resource_types=ResourceType,
                availability_results=[]
            )

        try:

            resource_type_enum = ResourceType(
                resource_type
            )

        except ValueError:

            flash(
                "Invalid resource type selected.",
                "error"
            )

            return render_template(
                "availability_check.html",
                resources=resources,
                resource_types=ResourceType,
                availability_results=[]
            )

        # ------------------------------------------
        # Validate dates
        # ------------------------------------------

        if not start_value or not end_value:

            flash(
                "Start and end times are required.",
                "error"
            )

            return render_template(
                "availability_check.html",
                resources=resources,
                resource_types=ResourceType,
                availability_results=[]
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
                "error"
            )

            return render_template(
                "availability_check.html",
                resources=resources,
                resource_types=ResourceType,
                availability_results=[]
            )

        if end_dt <= start_dt:

            flash(
                "End time must be after start time.",
                "error"
            )

            return render_template(
                "availability_check.html",
                resources=resources,
                resource_types=ResourceType,
                availability_results=[]
            )

        # ------------------------------------------
        # Validate attendance
        # ------------------------------------------

        attendance_value = 0

        if attendance:

            try:

                attendance_value = int(
                    attendance
                )

            except ValueError:

                flash(
                    "Attendance must be a valid number.",
                    "error"
                )

                return render_template(
                    "availability_check.html",
                    resources=resources,
                    resource_types=ResourceType,
                    availability_results=[]
                )

            if attendance_value < 0:

                flash(
                    "Attendance cannot be negative.",
                    "error"
                )

                return render_template(
                    "availability_check.html",
                    resources=resources,
                    resource_types=ResourceType,
                    availability_results=[]
                )

        # ------------------------------------------
        # Find matching active resources
        # ------------------------------------------

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

        for resource in matching_resources:

            # --------------------------------------
            # Capacity check
            # --------------------------------------

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
                            f"attendance {attendance_value}."
                        ),
                    }
                )

                continue

            # --------------------------------------
            # Conflict + buffer check
            # --------------------------------------

            conflicts = find_conflicts(
                session=db.session,
                resource_id=resource.id,
                start=start_dt,
                end=end_dt,
            )

            if conflicts:

                availability_results.append(
                    {
                        "resource": resource,
                        "available": False,
                        "reason": (
                            "Resource is booked or "
                            "within its buffer period."
                        ),
                    }
                )

                continue

            # --------------------------------------
            # Resource is available
            # --------------------------------------

            availability_results.append(
                {
                    "resource": resource,
                    "available": True,
                    "reason": (
                        "Resource is available for "
                        "the requested time."
                    ),
                }
            )

    return render_template(
        "availability_check.html",
        resources=resources,
        resource_types=ResourceType,
        availability_results=availability_results,
    )
