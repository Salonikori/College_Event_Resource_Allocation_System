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
    Event,
    EventStatus,
)

from app.services.status import (
    InvalidStatusTransition,
    get_allowed_event_statuses,
    transition_event_status,
)


events_bp = Blueprint(
    "events",
    __name__,
    url_prefix="/events",
)


# ============================================================
# HELPERS
# ============================================================

def parse_event_form():
    """
    Read and validate event form data.

    Returns:
        (data, error)
    """

    name = request.form.get(
        "name",
        "",
    ).strip()

    organizer = request.form.get(
        "organizer",
        "",
    ).strip()

    attendance = request.form.get(
        "expected_attendance",
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

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    if not name:
        return None, "Event name is required."

    if not organizer:
        return None, "Organizer name is required."

    if not attendance:
        return None, "Expected attendance is required."

    if not start_value or not end_value:
        return None, "Start and end time are required."

    # --------------------------------------------------------
    # Attendance
    # --------------------------------------------------------

    try:
        expected_attendance = int(attendance)

    except (ValueError, TypeError):
        return None, (
            "Expected attendance must be a valid number."
        )

    if expected_attendance <= 0:
        return None, (
            "Expected attendance must be greater than zero."
        )

    # --------------------------------------------------------
    # Date/time
    # --------------------------------------------------------

    try:
        start_dt = datetime.fromisoformat(
            start_value
        )

        end_dt = datetime.fromisoformat(
            end_value
        )

    except ValueError:
        return None, (
            "Please enter valid start and end dates."
        )

    if end_dt <= start_dt:
        return None, (
            "End time must be after start time."
        )

    return {
        "name": name,
        "organizer": organizer,
        "expected_attendance": expected_attendance,
        "start_dt": start_dt,
        "end_dt": end_dt,
    }, None


def get_event_form_data(event):
    """
    Convert an Event object into values suitable for
    datetime-local inputs.
    """

    return {
        "name": event.name,
        "organizer": event.organizer,
        "expected_attendance": event.expected_attendance,

        "start_dt": event.start_dt.strftime(
            "%Y-%m-%dT%H:%M"
        ),

        "end_dt": event.end_dt.strftime(
            "%Y-%m-%dT%H:%M"
        ),

        "status": event.status.value,
    }


# ============================================================
# LIST EVENTS + FILTER
# ============================================================

@events_bp.route("/")
def events():

    status_filter = request.args.get(
        "status",
        "",
    ).strip()

    from_date = request.args.get(
        "from_date",
        "",
    ).strip()

    to_date = request.args.get(
        "to_date",
        "",
    ).strip()

    query = Event.query

    # --------------------------------------------------------
    # STATUS FILTER
    # --------------------------------------------------------

    if status_filter:

        try:
            status_enum = EventStatus(
                status_filter
            )

            query = query.filter(
                Event.status == status_enum
            )

        except ValueError:

            flash(
                "Invalid event status filter.",
                "error",
            )

    # --------------------------------------------------------
    # FROM DATE
    #
    # Include events that overlap the selected date.
    #
    # Event must end on/after from_date.
    # --------------------------------------------------------

    if from_date:

        try:
            from_datetime = datetime.strptime(
                from_date,
                "%Y-%m-%d",
            )

            query = query.filter(
                Event.end_dt >= from_datetime
            )

        except ValueError:

            flash(
                "Invalid from date.",
                "error",
            )

    # --------------------------------------------------------
    # TO DATE
    #
    # Include the entire selected day.
    #
    # Event must start on/before to_date.
    # --------------------------------------------------------

    if to_date:

        try:
            to_datetime = datetime.strptime(
                to_date,
                "%Y-%m-%d",
            )

            to_datetime = to_datetime.replace(
                hour=23,
                minute=59,
                second=59,
                microsecond=999999,
            )

            query = query.filter(
                Event.start_dt <= to_datetime
            )

        except ValueError:

            flash(
                "Invalid to date.",
                "error",
            )

    # --------------------------------------------------------
    # INVALID DATE RANGE
    # --------------------------------------------------------

    if from_date and to_date:

        try:
            from_check = datetime.strptime(
                from_date,
                "%Y-%m-%d",
            )

            to_check = datetime.strptime(
                to_date,
                "%Y-%m-%d",
            )

            if from_check > to_check:

                flash(
                    "From date cannot be after to date.",
                    "error",
                )

                query = Event.query

        except ValueError:
            pass

    events = (
        query
        .order_by(
            Event.start_dt.asc()
        )
        .all()
    )

    return render_template(
        "events.html",
        events=events,
        status_filter=status_filter,
        from_date=from_date,
        to_date=to_date,
        event_statuses=EventStatus,
    )


# ============================================================
# CREATE EVENT
# ============================================================

@events_bp.route(
    "/create",
    methods=["GET", "POST"],
)
def create_event():

    if request.method == "POST":

        data, error = parse_event_form()

        if error:

            flash(
                error,
                "error",
            )

            return render_template(
                "event_form.html",
                event=None,
                form_data=request.form,
                allowed_statuses=[],
            )

        event = Event(
            name=data["name"],
            organizer=data["organizer"],
            expected_attendance=data[
                "expected_attendance"
            ],
            start_dt=data["start_dt"],
            end_dt=data["end_dt"],
            status=EventStatus.DRAFT,
        )

        db.session.add(event)
        db.session.commit()

        flash(
            "Event created successfully.",
            "success",
        )

        return redirect(
            url_for("events.events")
        )

    return render_template(
        "event_form.html",
        event=None,
        form_data={},
        allowed_statuses=[],
    )


# ============================================================
# EDIT EVENT
# ============================================================

@events_bp.route(
    "/<int:event_id>/edit",
    methods=["GET", "POST"],
)
def edit_event(event_id):

    event = db.session.get(
        Event,
        event_id,
    )

    if event is None:

        flash(
            "Event not found.",
            "error",
        )

        return redirect(
            url_for("events.events")
        )

    # --------------------------------------------------------
    # Cancelled/completed events cannot be edited.
    # --------------------------------------------------------

    if event.status in (
        EventStatus.CANCELLED,
        EventStatus.COMPLETED,
    ):

        flash(
            "Cancelled or completed events cannot be edited.",
            "error",
        )

        return redirect(
            url_for("events.events")
        )

    # --------------------------------------------------------
    # Allowed status options
    #
    # Current status is always allowed to remain unchanged.
    # --------------------------------------------------------

    allowed_statuses = [
        event.status
    ]

    allowed_statuses.extend(
        get_allowed_event_statuses(
            event.status
        )
    )

    # Remove duplicates while preserving order.
    allowed_statuses = list(
        dict.fromkeys(allowed_statuses)
    )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        data, error = parse_event_form()

        if error:

            flash(
                error,
                "error",
            )

            return render_template(
                "event_form.html",
                event=event,
                form_data=request.form,
                allowed_statuses=allowed_statuses,
            )

        requested_status = request.form.get(
            "status",
            event.status.value,
        ).strip()

        try:

            new_status = EventStatus(
                requested_status
            )

        except ValueError:

            flash(
                "Invalid event status selected.",
                "error",
            )

            return render_template(
                "event_form.html",
                event=event,
                form_data=request.form,
                allowed_statuses=allowed_statuses,
            )

        # ----------------------------------------------------
        # Validate status transition
        # ----------------------------------------------------

        if new_status != event.status:

            try:

                event.status = transition_event_status(
                    event.status,
                    new_status,
                )

            except InvalidStatusTransition as error:

                flash(
                    str(error),
                    "error",
                )

                return render_template(
                    "event_form.html",
                    event=event,
                    form_data=request.form,
                    allowed_statuses=allowed_statuses,
                )

        # ----------------------------------------------------
        # Update fields
        # ----------------------------------------------------

        event.name = data["name"]

        event.organizer = data[
            "organizer"
        ]

        event.expected_attendance = data[
            "expected_attendance"
        ]

        event.start_dt = data[
            "start_dt"
        ]

        event.end_dt = data[
            "end_dt"
        ]

        try:

            db.session.commit()

        except Exception:

            db.session.rollback()

            flash(
                "Unable to update the event.",
                "error",
            )

            return render_template(
                "event_form.html",
                event=event,
                form_data=request.form,
                allowed_statuses=allowed_statuses,
            )

        flash(
            "Event updated successfully.",
            "success",
        )

        return redirect(
            url_for("events.events")
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    form_data = get_event_form_data(
        event
    )

    return render_template(
        "event_form.html",
        event=event,
        form_data=form_data,
        allowed_statuses=allowed_statuses,
    )


# ============================================================
# CANCEL EVENT
# ============================================================

@events_bp.route(
    "/<int:event_id>/cancel",
    methods=["POST"],
)
def cancel_event(event_id):

    event = db.session.get(
        Event,
        event_id,
    )

    if event is None:

        flash(
            "Event not found.",
            "error",
        )

        return redirect(
            url_for("events.events")
        )

    # --------------------------------------------------------
    # Already cancelled
    # --------------------------------------------------------

    if event.status == EventStatus.CANCELLED:

        flash(
            "Event is already cancelled.",
            "info",
        )

        return redirect(
            url_for("events.events")
        )

    # --------------------------------------------------------
    # Completed events cannot be cancelled
    # --------------------------------------------------------

    if event.status == EventStatus.COMPLETED:

        flash(
            "Completed events cannot be cancelled.",
            "error",
        )

        return redirect(
            url_for("events.events")
        )

    try:

        event.status = EventStatus.CANCELLED

        # ----------------------------------------------------
        # Release active allocations.
        #
        # Historical allocation rows are retained.
        # ----------------------------------------------------

        allocations = (
            Allocation.query
            .filter(
                Allocation.event_id == event.id,
                Allocation.status.in_(
                    [
                        AllocationStatus.ALLOCATED,
                        AllocationStatus.APPROVED,
                    ]
                ),
            )
            .all()
        )

        for allocation in allocations:

            allocation.status = (
                AllocationStatus.CANCELLED
            )

        db.session.commit()

    except Exception:

        db.session.rollback()

        flash(
            "Unable to cancel the event.",
            "error",
        )

        return redirect(
            url_for("events.events")
        )

    flash(
        "Event cancelled and allocated resources released.",
        "success",
    )

    return redirect(
        url_for("events.events")
    )