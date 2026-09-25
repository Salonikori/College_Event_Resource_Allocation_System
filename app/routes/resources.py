from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app import db

from app.decorators import admin_required

from app.models import (
    Allocation,
    AllocationStatus,
    Resource,
    ResourceType,
)


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
    # NAME
    # --------------------------------------------------------

    if not name:

        return None, (
            "Resource name is required."
        )

    # --------------------------------------------------------
    # TYPE
    # --------------------------------------------------------

    if not resource_type:

        return None, (
            "Resource type is required."
        )

    try:

        resource_type_enum = ResourceType(
            resource_type
        )

    except ValueError:

        return None, (
            "Invalid resource type selected."
        )

    # --------------------------------------------------------
    # CAPACITY
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
    # BUFFER
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
@admin_required
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
            buffer_minutes=data[
                "buffer_minutes"
            ],
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
# EDIT RESOURCE
# ============================================================

@resources_bp.route(
    "/<int:resource_id>/edit",
    methods=["POST"],
)
@admin_required
def edit_resource(resource_id):

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
    # Protect active allocations from incompatible edits.
    # Changing type/capacity while a resource is allocated can
    # invalidate the suitability assumptions of an existing
    # booking. Name and buffer can safely be changed.
    # --------------------------------------------------------

    active_allocations = (
        Allocation.query
        .filter(
            Allocation.resource_id == resource.id,
            Allocation.status.in_(
                [
                    AllocationStatus.ALLOCATED,
                    AllocationStatus.APPROVED,
                ]
            ),
        )
        .count()
    )

    if active_allocations and (
        data["type"] != resource.type
        or data["capacity"] != resource.capacity
    ):
        flash(
            "This resource has active allocations. Cancel/release "
            "those allocations before changing its type or capacity.",
            "error",
        )
        return redirect(url_for("resources.resources"))

    # --------------------------------------------------------
    # Update existing resource.
    # --------------------------------------------------------

    resource.name = data["name"]
    resource.type = data["type"]
    resource.capacity = data["capacity"]
    resource.buffer_minutes = data["buffer_minutes"]

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        flash(
            "Unable to update the resource.",
            "error",
        )

        return redirect(
            url_for(
                "resources.resources"
            )
        )

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
@admin_required
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

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        flash(
            "Unable to activate the resource.",
            "error",
        )

        return redirect(
            url_for(
                "resources.resources"
            )
        )

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
@admin_required
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
    # Existing allocations are NOT deleted.
    #
    # Deactivation only prevents NEW allocations.
    # --------------------------------------------------------

    resource.is_active = False

    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        flash(
            "Unable to deactivate the resource.",
            "error",
        )

        return redirect(
            url_for(
                "resources.resources"
            )
        )

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
# LEGACY AVAILABILITY REDIRECT
# ============================================================
#
# The application now has a dedicated availability blueprint:
#
#     /availability/
#
# Keep these routes only as compatibility redirects so old
# links do not cause template errors.
# ============================================================

@resources_bp.route(
    "/availability",
    methods=["GET"],
)
def availability():

    return redirect(
        url_for(
            "availability.availability"
        )
    )


@resources_bp.route(
    "/availability/check",
    methods=["GET", "POST"],
)
def check_availability():

    return redirect(
        url_for(
            "availability.availability"
        )
    )