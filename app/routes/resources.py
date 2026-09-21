from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import Resource, ResourceType


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
    resources = Resource.query.order_by(Resource.name.asc()).all()

    return render_template(
        "resources.html",
        resources=resources
    )


# --------------------------------------------------
# Create a new resource
# --------------------------------------------------
@resources_bp.route("/create", methods=["GET", "POST"])
def create_resource():

    if request.method == "POST":

        # Get form values
        name = request.form.get("name", "").strip()
        resource_type = request.form.get("type", "").strip()
        capacity = request.form.get("capacity", "").strip()
        buffer_minutes = request.form.get("buffer_minutes", "0").strip()

        # ------------------------------------------
        # Basic validation
        # ------------------------------------------

        if not name:
            flash("Resource name is required.", "error")
            return render_template(
                "resource_form.html",
                resource_types=ResourceType
            )

        if not resource_type:
            flash("Resource type is required.", "error")
            return render_template(
                "resource_form.html",
                resource_types=ResourceType
            )

        # ------------------------------------------
        # Validate resource type
        # ------------------------------------------

        try:
            resource_type_enum = ResourceType(resource_type)

        except ValueError:
            flash("Invalid resource type selected.", "error")
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
                buffer_value = int(buffer_minutes)

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
        # Create Resource
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

        # ------------------------------------------
        # Success
        # ------------------------------------------

        flash(
            "Resource created successfully.",
            "success"
        )

        return redirect(
            url_for("resources.resources")
        )

    # GET request
    return render_template(
        "resource_form.html",
        resource_types=ResourceType
    )