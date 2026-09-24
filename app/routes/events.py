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


events_bp = Blueprint(
    "events",
    __name__,
    url_prefix="/events"
)


# ============================================================
# HELPERS
# ============================================================

def parse_event_form():
    """
    Read and validate event form data.

    Returns:
        (data, error)

    data contains:
        name
        organizer
        expected_attendance
        start_dt
        end_dt
    """

    name = request.form.get("name", "").strip()
    organizer = request.form.get("organizer", "").strip()
    attendance = request.form.get(
        "expected_attendance",
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

    except ValueError:
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


# ============================================================
# LIST EVENTS + FILTER
# ============================================================

@events_bp.route("/")
def events():

    status_filter = request.args.get(
        "status",
        ""
    ).strip()

    from_date = request.args.get(
        "from_date",
        ""
    ).strip()

    to_date = request.args.get(
        "to_date",
        ""
    ).strip()

    query = Event.query

    # --------------------------------------------------------
    # Status filter
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
                "error"
            )

    # --------------------------------------------------------
    # From date
    # --------------------------------------------------------

    if from_date:

        try:
            from_datetime = datetime.fromisoformat(
                from_date
            )

            query = query.filter(
                Event.start_dt >= from_datetime
            )

        except ValueError:

            flash(
                "Invalid from date.",
                "error"
            )

    # --------------------------------------------------------
    # To date
    # --------------------------------------------------------

    if to_date:

        try:
            to_datetime = datetime.fromisoformat(
                to_date
            )

            # Include the entire selected day.
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
                "error"
            )

    events = query.order_by(
        Event.start_dt.asc()
    ).all()

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
    methods=["GET", "POST"]
)
def create_event():

    if request.method == "POST":

        data, error = parse_event_form()

        if error:

            flash(
                error,
                "error"
            )

            return render_template(
                "event_form.html",
                event=None,
                form_data=request.form,
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
            "success"
        )

        return redirect(
            url_for("events.events")
        )

    return render_template(
        "event_form.html",
        event=None,
        form_data={},
    )


# ============================================================
# EDIT EVENT
# ============================================================

@events_bp.route(
    "/<int:event_id>/edit",
    methods=["GET", "POST"]
)
def edit_event(event_id):

    event = db.session.get(
        Event,
        event_id
    )

    if event is None:

        flash(
            "Event not found.",
            "error"
        )

        return redirect(
            url_for("events.events")
        )

    # --------------------------------------------------------
    # Prevent editing cancelled/completed events
    # --------------------------------------------------------

    if event.status in (
        EventStatus.CANCELLED,
        EventStatus.COMPLETED,
    ):

        flash(
            "Cancelled or completed events cannot be edited.",
            "error"
        )

        return redirect(
            url_for("events.events")
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        data, error = parse_event_form()

        if error:

            flash(
                error,
                "error"
            )

            return render_template(
                "event_form.html",
                event=event,
                form_data=request.form,
            )

        # ----------------------------------------------------
        # Update event
        # ----------------------------------------------------

        event.name = data["name"]
        event.organizer = data["organizer"]
        event.expected_attendance = data[
            "expected_attendance"
        ]
        event.start_dt = data["start_dt"]
        event.end_dt = data["end_dt"]

        db.session.commit()

        flash(
            "Event updated successfully.",
            "success"
        )

        return redirect(
            url_for("events.events")
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    form_data = {
        "name": event.name,
        "organizer": event.organizer,
        "expected_attendance": event.expected_attendance,
        "start_dt": event.start_dt.strftime(
            "%Y-%m-%dT%H:%M"
        ),
        "end_dt": event.end_dt.strftime(
            "%Y-%m-%dT%H:%M"
        ),
    }

    return render_template(
        "event_form.html",
        event=event,
        form_data=form_data,
    )


# ============================================================
# CANCEL EVENT
# ============================================================

@events_bp.route(
    "/<int:event_id>/cancel",
    methods=["POST"]
)
def cancel_event(event_id):

    event = db.session.get(
        Event,
        event_id
    )

    if event is None:

        flash(
            "Event not found.",
            "error"
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
            "info"
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
            "error"
        )

        return redirect(
            url_for("events.events")
        )

    # --------------------------------------------------------
    # Cancel event
    # --------------------------------------------------------

    event.status = EventStatus.CANCELLED

    # --------------------------------------------------------
    # Release active allocations
    # --------------------------------------------------------

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

    flash(
        "Event cancelled and allocated resources released.",
        "success"
    )

    return redirect(
        url_for("events.events")
    )