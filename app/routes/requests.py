
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
    Event,
    RequestItem,
    RequestStatus,
    ResourceRequest,
    ResourceType,
)
from app.services.alternatives import get_resource_alternatives


requests_bp = Blueprint(
    "requests",
    __name__,
    url_prefix="/requests"
)


# --------------------------------------------------
# List all resource requests
# --------------------------------------------------
@requests_bp.route("/")
def requests():

    requests_list = (
        ResourceRequest.query
        .order_by(ResourceRequest.created_at.desc())
        .all()
    )

    return render_template(
        "requests.html",
        requests=requests_list
    )


# --------------------------------------------------
# Create a new resource request
# --------------------------------------------------
@requests_bp.route("/create", methods=["GET", "POST"])
def create_request():

    events = (
        Event.query
        .order_by(Event.start_dt.asc())
        .all()
    )

    if request.method == "POST":

        # ------------------------------------------
        # Get form values
        # ------------------------------------------

        event_id = request.form.get(
            "event_id",
            ""
        ).strip()

        resource_type = request.form.get(
            "resource_type",
            ""
        ).strip()

        quantity = request.form.get(
            "quantity",
            ""
        ).strip()

        start_value = request.form.get(
            "requested_start",
            ""
        ).strip()

        end_value = request.form.get(
            "requested_end",
            ""
        ).strip()

        # ------------------------------------------
        # Validate event
        # ------------------------------------------

        if not event_id:

            flash(
                "Please select an event.",
                "error"
            )

            return render_template(
                "request_form.html",
                events=events,
                resource_types=ResourceType
            )

        try:

            event_id_value = int(event_id)

        except ValueError:

            flash(
                "Invalid event selected.",
                "error"
            )

            return render_template(
                "request_form.html",
                events=events,
                resource_types=ResourceType
            )

        event = db.session.get(
            Event,
            event_id_value
        )

        if event is None:

            flash(
                "Selected event does not exist.",
                "error"
            )

            return render_template(
                "request_form.html",
                events=events,
                resource_types=ResourceType
            )

        # ------------------------------------------
        # Validate resource type
        # ------------------------------------------

        if not resource_type:

            flash(
                "Please select a resource type.",
                "error"
            )

            return render_template(
                "request_form.html",
                events=events,
                resource_types=ResourceType
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
                "request_form.html",
                events=events,
                resource_types=ResourceType
            )

        # ------------------------------------------
        # Validate quantity
        # ------------------------------------------

        if not quantity:

            flash(
                "Quantity is required.",
                "error"
            )

            return render_template(
                "request_form.html",
                events=events,
                resource_types=ResourceType
            )

        try:

            quantity_value = int(quantity)

        except ValueError:

            flash(
                "Quantity must be a valid number.",
                "error"
            )

            return render_template(
                "request_form.html",
                events=events,
                resource_types=ResourceType
            )

        if quantity_value <= 0:

            flash(
                "Quantity must be greater than zero.",
                "error"
            )

            return render_template(
                "request_form.html",
                events=events,
                resource_types=ResourceType
            )

        # ------------------------------------------
        # Validate dates
        # ------------------------------------------

        if not start_value or not end_value:

            flash(
                "Requested start and end times are required.",
                "error"
            )

            return render_template(
                "request_form.html",
                events=events,
                resource_types=ResourceType
            )

        try:

            requested_start = datetime.fromisoformat(
                start_value
            )

            requested_end = datetime.fromisoformat(
                end_value
            )

        except ValueError:

            flash(
                "Please enter valid start and end dates.",
                "error"
            )

            return render_template(
                "request_form.html",
                events=events,
                resource_types=ResourceType
            )

        if requested_end <= requested_start:

            flash(
                "End time must be after start time.",
                "error"
            )

            return render_template(
                "request_form.html",
                events=events,
                resource_types=ResourceType
            )

        # ------------------------------------------
        # Create Resource Request
        # ------------------------------------------

        resource_request = ResourceRequest(
            event_id=event.id,
            requested_start=requested_start,
            requested_end=requested_end,
            status=RequestStatus.PENDING
        )

        db.session.add(resource_request)

        # Flush so the request gets its database ID
        db.session.flush()

        # ------------------------------------------
        # Create Request Item
        # ------------------------------------------

        request_item = RequestItem(
            request_id=resource_request.id,
            resource_type=resource_type_enum,
            quantity=quantity_value
        )

        db.session.add(request_item)

        # ------------------------------------------
        # Save everything
        # ------------------------------------------

        db.session.commit()

        flash(
            "Resource request created successfully.",
            "success"
        )

        return redirect(
            url_for("requests.requests")
        )

    # ------------------------------------------
    # GET request
    # ------------------------------------------

    return render_template(
        "request_form.html",
        events=events,
        resource_types=ResourceType
    )


# --------------------------------------------------
# Show resource alternatives
# --------------------------------------------------
@requests_bp.route(
    "/<int:request_id>/alternatives"
)
def alternatives(request_id):

    resource_request = db.session.get(
        ResourceRequest,
        request_id
    )

    if resource_request is None:

        flash(
            "Resource request not found.",
            "error"
        )

        return redirect(
            url_for("requests.requests")
        )

    # ------------------------------------------
    # Get request event
    # ------------------------------------------

    event = resource_request.event

    # ------------------------------------------
    # Get request items
    # ------------------------------------------

    request_items = list(
        resource_request.items
    )

    if not request_items:

        flash(
            "This request has no resource items.",
            "error"
        )

        return redirect(
            url_for("requests.requests")
        )

    # ------------------------------------------
    # Generate alternatives for every item
    # ------------------------------------------

    alternatives = []

    for item in request_items:

        result = get_resource_alternatives(
            session=db.session,
            event=event,
            required_type=item.resource_type,
            start_dt=resource_request.requested_start,
            end_dt=resource_request.requested_end,
        )

        alternatives.append(
            {
                "item": item,
                "exact_time": result["exact_time"],
                "nearby_time": result["nearby_time"],
            }
        )

    return render_template(
        "request_alternatives.html",
        resource_request=resource_request,
        event=event,
        alternatives=alternatives,
    )
