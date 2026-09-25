from datetime import datetime, timedelta

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from flask_login import current_user

from app import db

from app.models import (
    Event,
    EventStatus,
    RequestItem,
    RequestStatus,
    Resource,
    ResourceRequest,
    ResourceType,
    Recurrence,
    WaitlistStatus,
    WaitlistEntry,
)

from app.services.alternatives import get_resource_alternatives
from app.services.booking import AllocationError, pick_resources
from app.services.waitlist import add_to_waitlist


requests_bp = Blueprint(
    "requests",
    __name__,
    url_prefix="/requests",
)


# ============================================================
# HELPERS
# ============================================================

def _load_form_data():
    """
    Preserve submitted values so the form can be re-rendered
    after a validation error.
    """

    return {
        "event_id": request.form.get(
            "event_id",
            "",
        ),

        "requested_start": request.form.get(
            "requested_start",
            "",
        ),

        "requested_end": request.form.get(
            "requested_end",
            "",
        ),

        "resource_types": request.form.getlist(
            "resource_type"
        ),

        "quantities": request.form.getlist(
            "quantity"
        ),

        "specific_resource_ids": request.form.getlist(
            "specific_resource_id"
        ),

        "recurrence_frequency": request.form.get("recurrence_frequency", "NONE"),
        "recurrence_count": request.form.get("recurrence_count", "1"),
        "waitlist_on_conflict": request.form.get("waitlist_on_conflict", "") ,
    }


def _render_request_form(
    events,
    resources,
    form_data=None,
    status_code=200,
):
    """
    Render the request form.
    """

    return render_template(
        "request_form.html",
        events=events,
        resources=resources,
        resource_types=ResourceType,
        form_data=form_data or {},
    ), status_code


def _error(
    events,
    resources,
    message,
    form_data=None,
    status_code=400,
):
    """
    Roll back the current transaction, show an error and
    return the form with HTTP 400.
    """

    db.session.rollback()

    flash(
        message,
        "error",
    )

    return _render_request_form(
        events,
        resources,
        form_data=form_data,
        status_code=status_code,
    )


def _parse_resource_rows():
    """
    Parse multiple resource rows submitted by the form.

    Example:

        resource_type = HALL
        quantity = 1

        resource_type = PROJECTOR
        quantity = 1

        resource_type = MICROPHONE
        quantity = 2

    Flask's getlist() is used so the backend supports
    multiple rows with the same field name.
    """

    resource_types = request.form.getlist(
        "resource_type"
    )

    quantities = request.form.getlist(
        "quantity"
    )

    specific_ids = request.form.getlist(
        "specific_resource_id"
    )

    # --------------------------------------------------------
    # Also support [] style field names
    # --------------------------------------------------------

    if not resource_types:

        resource_types = request.form.getlist(
            "resource_type[]"
        )

    if not quantities:

        quantities = request.form.getlist(
            "quantity[]"
        )

    if not specific_ids:

        specific_ids = request.form.getlist(
            "specific_resource_id[]"
        )

    # --------------------------------------------------------
    # Keep row alignment
    # --------------------------------------------------------

    while len(specific_ids) < len(resource_types):

        specific_ids.append("")

    # --------------------------------------------------------
    # Validate number of fields
    # --------------------------------------------------------

    if len(resource_types) != len(quantities):

        raise ValueError(
            "Each resource row must contain both "
            "a resource type and a quantity."
        )

    if not resource_types:

        raise ValueError(
            "Please add at least one resource."
        )

    # --------------------------------------------------------
    # Build rows
    # --------------------------------------------------------

    rows = []

    for index in range(
        len(resource_types)
    ):

        rows.append(
            {
                "resource_type":
                    resource_types[index].strip(),

                "quantity":
                    quantities[index].strip(),

                "specific_resource_id":
                    specific_ids[index].strip(),
            }
        )

    return rows


def _validate_resource_rows(
    event,
    rows,
):
    """
    Validate all requested resource rows.

    Rules:

    - Valid ResourceType
    - Quantity must be positive integer
    - No duplicate resource type rows
    - Specific resource must exist
    - Specific resource must be active
    - Specific resource type must match
    - Specific resource quantity must be 1
    - Same physical resource cannot be selected twice
    - Cancelled events cannot receive requests
    """

    validated_rows = []

    seen_types = set()

    planned_resource_ids = set()

    # --------------------------------------------------------
    # Event status
    # --------------------------------------------------------

    if event.status.value == "CANCELLED":

        raise ValueError(
            f"Event '{event.name}' is cancelled and "
            "cannot receive new resource requests."
        )

    if event.status.value == "REJECTED":

        raise ValueError(
            f"Event '{event.name}' is rejected and "
            "cannot receive new resource requests."
        )

    # --------------------------------------------------------
    # Validate every row
    # --------------------------------------------------------

    for index, row in enumerate(
        rows,
        start=1,
    ):

        resource_type_value = row[
            "resource_type"
        ]

        quantity_value = row[
            "quantity"
        ]

        specific_resource_id = row[
            "specific_resource_id"
        ]

        # ----------------------------------------------------
        # Resource type
        # ----------------------------------------------------

        if not resource_type_value:

            raise ValueError(
                f"Resource row {index}: "
                "select a resource type."
            )

        try:

            resource_type = ResourceType(
                resource_type_value
            )

        except ValueError:

            raise ValueError(
                f"Resource row {index}: "
                f"invalid resource type "
                f"'{resource_type_value}'."
            )

        # ----------------------------------------------------
        # Duplicate resource type
        # ----------------------------------------------------

        if resource_type in seen_types:

            raise ValueError(
                f"Resource type "
                f"'{resource_type.value}' "
                "was added more than once. "
                "Increase its quantity instead of "
                "adding a duplicate row."
            )

        seen_types.add(
            resource_type
        )

        # ----------------------------------------------------
        # Quantity
        # ----------------------------------------------------

        if not quantity_value:

            raise ValueError(
                f"Resource row {index}: "
                "quantity is required."
            )

        try:

            quantity = int(
                quantity_value
            )

        except ValueError:

            raise ValueError(
                f"Resource row {index}: "
                "quantity must be a whole number."
            )

        if quantity <= 0:

            raise ValueError(
                f"Resource row {index}: "
                "quantity must be greater than zero."
            )

        if quantity > 1000:

            raise ValueError(
                f"Resource row {index}: "
                "quantity is too large."
            )

        # ----------------------------------------------------
        # Specific resource
        # ----------------------------------------------------

        specific_resource = None

        if specific_resource_id:

            try:

                resource_id = int(
                    specific_resource_id
                )

            except ValueError:

                raise ValueError(
                    f"Resource row {index}: "
                    "invalid specific resource selected."
                )

            specific_resource = db.session.get(
                Resource,
                resource_id,
            )

            if specific_resource is None:

                raise ValueError(
                    f"Resource row {index}: "
                    "selected resource does not exist."
                )

            if not specific_resource.is_active:

                raise ValueError(
                    f"Resource row {index}: "
                    "selected resource is inactive."
                )

            if (
                specific_resource.type
                != resource_type
            ):

                raise ValueError(
                    f"Resource row {index}: "
                    "selected resource does not match "
                    "the selected resource type."
                )

            # A specific physical resource is one resource.
            if quantity != 1:

                raise ValueError(
                    f"Resource row {index}: "
                    "quantity must be 1 when a "
                    "specific resource is selected."
                )

            if (
                specific_resource.id
                in planned_resource_ids
            ):

                raise ValueError(
                    f"Resource row {index}: "
                    "the same specific resource "
                    "was selected twice."
                )

            planned_resource_ids.add(
                specific_resource.id
            )

        # ----------------------------------------------------
        # Store validated row
        # ----------------------------------------------------

        validated_rows.append(
            {
                "resource_type":
                    resource_type,

                "quantity":
                    quantity,

                "specific_resource_id":
                    (
                        specific_resource.id
                        if specific_resource
                        else None
                    ),
            }
        )

    return (
        validated_rows,
        planned_resource_ids,
    )


def _validate_request_time(
    event,
    requested_start,
    requested_end,
):
    """
    Validate requested time against event time.
    """

    if requested_end <= requested_start:

        raise ValueError(
            "End time must be after start time."
        )

    if (
        requested_start < event.start_dt
        or requested_end > event.end_dt
    ):

        raise ValueError(
            "Requested allocation time must fall "
            "within the event start and end time."
        )


# ============================================================
# INLINE CONFLICT API
# ============================================================

@requests_bp.route("/api/conflicts", methods=["GET"])
def conflict_check():
    """Return active allocations overlapping a proposed period."""
    resource_id = request.args.get("resource_id", "").strip()
    resource_type_value = request.args.get("resource_type", "").strip()
    quantity = max(1, request.args.get("quantity", 1, type=int) or 1)
    start_value = request.args.get("start", "").strip()
    end_value = request.args.get("end", "").strip()

    if not start_value or not end_value:
        return jsonify({"error": "start and end are required."}), 400

    try:
        start = datetime.fromisoformat(start_value)
        end = datetime.fromisoformat(end_value)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid date/time."}), 400

    if end <= start:
        return jsonify({"conflicts": [], "available": True})

    from app.services.booking import find_conflicts

    if resource_id:
        try:
            resource_id_int = int(resource_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid resource id."}), 400
        resource = db.session.get(Resource, resource_id_int)
        if resource is None:
            return jsonify({"error": "Resource not found."}), 404
        conflicts = find_conflicts(db.session, resource.id, start, end)
        return jsonify({
            "resource_name": resource.name,
            "available": not conflicts and resource.is_active,
            "conflicts": [
                {
                    "event": c.event.name if c.event else f"Allocation #{c.id}",
                    "start": c.start_dt.strftime("%d %b, %I:%M %p"),
                    "end": c.end_dt.strftime("%I:%M %p"),
                }
                for c in conflicts
            ],
        })

    if not resource_type_value:
        return jsonify({"error": "resource_id or resource_type is required."}), 400

    try:
        resource_type = ResourceType(resource_type_value)
    except ValueError:
        return jsonify({"error": "Invalid resource type."}), 400

    resources_of_type = (
        Resource.query
        .filter(Resource.type == resource_type, Resource.is_active.is_(True))
        .order_by(Resource.name.asc())
        .all()
    )
    available = []
    busy = []
    for resource in resources_of_type:
        conflicts = find_conflicts(db.session, resource.id, start, end)
        if conflicts:
            busy.append((resource, conflicts))
        else:
            available.append(resource)

    return jsonify({
        "resource_type": resource_type.value,
        "required": quantity,
        "available_count": len(available),
        "available": len(available) >= quantity,
        "conflicts": [
            {
                "resource_name": resource.name,
                "event": c.event.name if c.event else f"Allocation #{c.id}",
                "start": c.start_dt.strftime("%d %b, %I:%M %p"),
                "end": c.end_dt.strftime("%I:%M %p"),
            }
            for resource, conflicts in busy
            for c in conflicts
        ],
    })


# ============================================================
# LIST REQUESTS
# ============================================================

@requests_bp.route("/")
def requests():

    query = ResourceRequest.query

    # ----------------------------------------------------
    # Organizers only see requests for their own events.
    # Admins see every request in the system.
    # ----------------------------------------------------

    if not current_user.is_admin():

        query = query.join(Event).filter(
            Event.organizer_id == current_user.id
        )

    requests_list = (
        query
        .order_by(
            ResourceRequest.created_at.desc()
        )
        .all()
    )

    return render_template(
        "requests.html",
        requests=requests_list,
    )


# ============================================================
# CREATE REQUEST
# ============================================================

@requests_bp.route(
    "/create",
    methods=["GET", "POST"],
)
def create_request():

    events_query = Event.query

    # Organizers may only request resources for their own
    # events. Admins may create requests for any event.

    if not current_user.is_admin():

        events_query = events_query.filter(
            Event.organizer_id == current_user.id
        )

    events = (
        events_query
        .order_by(
            Event.start_dt.asc()
        )
        .all()
    )

    # Only active resources are offered to users.
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

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        form_data = _load_form_data()

        # ----------------------------------------------------
        # Event
        # ----------------------------------------------------

        event_id = form_data[
            "event_id"
        ].strip()

        if not event_id:

            return _error(
                events,
                resources,
                "Please select an event.",
                form_data,
            )

        try:

            event_id_value = int(
                event_id
            )

        except ValueError:

            return _error(
                events,
                resources,
                "Invalid event selected.",
                form_data,
            )

        event = db.session.get(
            Event,
            event_id_value,
        )

        if event is None:

            return _error(
                events,
                resources,
                "Selected event does not exist.",
                form_data,
            )

        # ----------------------------------------------------
        # Ownership
        #
        # Organizers may only request resources for events
        # they own. This blocks a tampered event_id in the
        # submitted form as well as the dropdown itself.
        # ----------------------------------------------------

        if (
            not current_user.is_admin()
            and event.organizer_id != current_user.id
        ):

            return _error(
                events,
                resources,
                "You can only request resources for "
                "your own events.",
                form_data,
            )

        # ----------------------------------------------------
        # Date/time
        # ----------------------------------------------------

        start_value = form_data[
            "requested_start"
        ].strip()

        end_value = form_data[
            "requested_end"
        ].strip()

        if (
            not start_value
            or not end_value
        ):

            return _error(
                events,
                resources,
                "Requested start and end times are required.",
                form_data,
            )

        try:

            requested_start = datetime.fromisoformat(
                start_value
            )

            requested_end = datetime.fromisoformat(
                end_value
            )

        except ValueError:

            return _error(
                events,
                resources,
                "Please enter valid start and end dates.",
                form_data,
            )

        try:

            _validate_request_time(
                event,
                requested_start,
                requested_end,
            )

        except ValueError as exc:

            return _error(
                events,
                resources,
                str(exc),
                form_data,
            )

        # ----------------------------------------------------
        # Recurrence + waitlist preferences
        # ----------------------------------------------------

        recurrence_frequency = form_data.get("recurrence_frequency", "NONE").upper()
        if recurrence_frequency not in {"NONE", "WEEKLY", "BIWEEKLY"}:
            return _error(events, resources, "Invalid recurrence frequency.", form_data)

        try:
            recurrence_count = int(form_data.get("recurrence_count", "1") or 1)
        except ValueError:
            return _error(events, resources, "Recurrence count must be a whole number.", form_data)

        recurrence_count = max(1, min(recurrence_count, 12))
        waitlist_on_conflict = bool(form_data.get("waitlist_on_conflict"))

        # ----------------------------------------------------
        # Resource rows
        # ----------------------------------------------------

        try:

            rows = _parse_resource_rows()

            (
                validated_rows,
                planned_resource_ids,
            ) = _validate_resource_rows(
                event,
                rows,
            )

        except ValueError as exc:

            return _error(
                events,
                resources,
                str(exc),
                form_data,
            )

        # ====================================================
        # CREATE RESOURCE REQUEST
        # ====================================================

        resource_request = ResourceRequest(
            event_id=event.id,

            requested_start=requested_start,

            requested_end=requested_end,

            status=RequestStatus.PENDING,
        )

        db.session.add(
            resource_request
        )

        db.session.flush()

        try:

            # ------------------------------------------------
            # Create ALL RequestItems
            # ------------------------------------------------

            for row in validated_rows:

                request_item = RequestItem(
                    request_id=resource_request.id,

                    resource_type=row[
                        "resource_type"
                    ],

                    quantity=row[
                        "quantity"
                    ],

                    specific_resource_id=row[
                        "specific_resource_id"
                    ],
                )

                db.session.add(
                    request_item
                )

            db.session.flush()

            # ------------------------------------------------
            # Validate suitability + availability
            #
            # This uses the SAME resource-selection logic
            # used by the real allocation workflow.
            # ------------------------------------------------

            planned_resource_ids = set(
                planned_resource_ids
            )

            for item in list(
                resource_request.items
            ):

                selected_resources = pick_resources(
                    db.session,
                    item,
                    resource_request,
                    unavailable_resource_ids=
                        planned_resource_ids,
                )

                for resource in selected_resources:

                    planned_resource_ids.add(
                        resource.id
                    )

        except AllocationError as exc:

            if not waitlist_on_conflict:
                db.session.rollback()
                return _error(events, resources, str(exc), form_data)

            # Keep the pending request and place each requested resource type
            # on the waitlist. It will be retried automatically when a
            # conflicting allocation is released.
            for item in list(resource_request.items):
                add_to_waitlist(resource_request, item.resource_type, item.specific_resource_id)

            db.session.commit()
            flash(
                "The requested slot is busy. Your request was created and placed on the waitlist.",
                "warning",
            )
            return redirect(url_for("requests.requests"))

        except Exception:

            db.session.rollback()

            raise

        # ----------------------------------------------------
        # Generate recurring occurrences. Each occurrence is checked
        # independently, so one conflict does not hide the others.
        # ----------------------------------------------------

        created_occurrences = 1
        waitlisted_occurrences = 0
        skipped_occurrences = 0

        recurrence = None
        if recurrence_count > 1 and recurrence_frequency != "NONE":
            recurrence = Recurrence(
                frequency=recurrence_frequency,
                occurrences=recurrence_count,
                interval=2 if recurrence_frequency == "BIWEEKLY" else 1,
            )
            db.session.add(recurrence)
            db.session.flush()
            event.recurrence_id = recurrence.id
            resource_request.recurrence_id = recurrence.id if hasattr(resource_request, "recurrence_id") else None

            duration = requested_end - requested_start
            step_days = 14 if recurrence_frequency == "BIWEEKLY" else 7

            for occurrence_index in range(1, recurrence_count):
                shift = timedelta(days=step_days * occurrence_index)
                occurrence_start = requested_start + shift
                occurrence_end = requested_end + shift

                occurrence_event = Event(
                    name=f"{event.name} — Week {occurrence_index + 1}",
                    organizer=event.organizer,
                    organizer_id=event.organizer_id,
                    expected_attendance=event.expected_attendance,
                    start_dt=event.start_dt + shift,
                    end_dt=event.end_dt + shift,
                    status=event.status,
                    recurrence_id=recurrence.id,
                )
                db.session.add(occurrence_event)
                db.session.flush()

                occurrence_request = ResourceRequest(
                    event_id=occurrence_event.id,
                    requested_start=occurrence_start,
                    requested_end=occurrence_end,
                    status=RequestStatus.PENDING,
                )
                db.session.add(occurrence_request)
                db.session.flush()

                for row in validated_rows:
                    db.session.add(RequestItem(
                        request_id=occurrence_request.id,
                        resource_type=row["resource_type"],
                        quantity=row["quantity"],
                        specific_resource_id=row["specific_resource_id"],
                    ))
                db.session.flush()

                try:
                    planned = set()
                    for item in list(occurrence_request.items):
                        selected = pick_resources(
                            db.session, item, occurrence_request,
                            unavailable_resource_ids=planned,
                        )
                        planned.update(r.id for r in selected)
                    created_occurrences += 1
                except AllocationError:
                    if waitlist_on_conflict:
                        for item in list(occurrence_request.items):
                            add_to_waitlist(occurrence_request, item.resource_type, item.specific_resource_id)
                        waitlisted_occurrences += 1
                    else:
                        db.session.delete(occurrence_request)
                        db.session.delete(occurrence_event)
                        db.session.flush()
                        skipped_occurrences += 1

        db.session.commit()

        summary = "Resource request created successfully."
        if recurrence_count > 1 and recurrence_frequency != "NONE":
            summary += f" {created_occurrences} occurrence(s) created."
            if waitlisted_occurrences:
                summary += f" {waitlisted_occurrences} occurrence(s) added to the waitlist."
            if skipped_occurrences:
                summary += f" {skipped_occurrences} conflicting occurrence(s) skipped."

        flash(summary, "success")
        return redirect(url_for("requests.requests"))

    # ========================================================
    # GET
    # ========================================================

    return render_template(
        "request_form.html",

        events=events,

        resources=resources,

        resource_types=ResourceType,

        form_data={},
    )


# ============================================================
# WAITLIST
# ============================================================

@requests_bp.route("/waitlist")
def waitlist():
    query = WaitlistEntry.query
    if not current_user.is_admin():
        query = query.join(ResourceRequest).join(Event).filter(Event.organizer_id == current_user.id)
    entries = query.order_by(WaitlistEntry.created_at.asc()).all()
    return render_template("waitlist.html", entries=entries)


@requests_bp.route("/<int:request_id>/waitlist", methods=["POST"])
def join_waitlist(request_id):
    resource_request = db.session.get(ResourceRequest, request_id)
    if resource_request is None:
        flash("Resource request not found.", "error")
        return redirect(url_for("requests.requests"))
    if not current_user.is_admin() and resource_request.event.organizer_id != current_user.id:
        abort(403)
    if resource_request.status != RequestStatus.PENDING:
        flash(
            f"Only pending requests can join the waitlist. Current status: {resource_request.status.value.title()}.",
            "error",
        )
        return redirect(url_for("requests.requests"))
    if resource_request.event is None or resource_request.event.status in {
        EventStatus.CANCELLED,
        EventStatus.REJECTED,
    }:
        flash("Requests for cancelled or rejected events cannot be waitlisted.", "error")
        return redirect(url_for("requests.requests"))
    for item in resource_request.items:
        add_to_waitlist(resource_request, item.resource_type, item.specific_resource_id)
    db.session.commit()
    flash("Request added to the waitlist. ResourceHub will retry it when a matching resource is released.", "success")
    return redirect(url_for("requests.waitlist"))


# ============================================================
# SHOW ALTERNATIVES
# ============================================================

@requests_bp.route(
    "/<int:request_id>/alternatives"
)
def alternatives(request_id):

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
            url_for(
                "requests.requests"
            )
        )

    event = resource_request.event

    if (
        not current_user.is_admin()
        and event.organizer_id != current_user.id
    ):
        abort(403)

    request_items = list(
        resource_request.items
    )

    if not request_items:

        flash(
            "This request has no resource items.",
            "error",
        )

        return redirect(
            url_for(
                "requests.requests"
            )
        )

    alternatives = []

    for item in request_items:

        requested_resource = (
            item.specific_resource
            if item.specific_resource_id
            else None
        )

        result = get_resource_alternatives(
            session=db.session,

            event=event,

            required_type=item.resource_type,

            start_dt=resource_request.requested_start,

            end_dt=resource_request.requested_end,

            excluded_resource_id=(
                item.specific_resource_id
            ),
        )

        alternatives.append(
            {
                "item": item,

                "requested_resource":
                    requested_resource,

                "exact_time":
                    result["exact_time"],

                "nearby_time":
                    result["nearby_time"],
            }
        )

    return render_template(
        "request_alternatives.html",

        resource_request=
            resource_request,

        event=event,

        alternatives=
            alternatives,
    )