from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import Event, EventStatus


events_bp = Blueprint("events", __name__, url_prefix="/events")


# --------------------------------------------------
# List all events
# --------------------------------------------------
@events_bp.route("/")
def events():
    events = Event.query.order_by(Event.start_dt.asc()).all()

    return render_template(
        "events.html",
        events=events
    )


# --------------------------------------------------
# Create a new event
# --------------------------------------------------
@events_bp.route("/create", methods=["GET", "POST"])
def create_event():

    if request.method == "POST":

        # Get form values
        name = request.form.get("name", "").strip()
        organizer = request.form.get("organizer", "").strip()
        attendance = request.form.get("expected_attendance", "").strip()
        start_value = request.form.get("start_dt", "").strip()
        end_value = request.form.get("end_dt", "").strip()

        # ------------------------------------------
        # Basic validation
        # ------------------------------------------

        if not name:
            flash("Event name is required.", "error")
            return render_template("event_form.html")

        if not organizer:
            flash("Organizer name is required.", "error")
            return render_template("event_form.html")

        if not attendance:
            flash("Expected attendance is required.", "error")
            return render_template("event_form.html")

        if not start_value or not end_value:
            flash("Start and end time are required.", "error")
            return render_template("event_form.html")

        # ------------------------------------------
        # Validate attendance
        # ------------------------------------------

        try:
            expected_attendance = int(attendance)

        except ValueError:
            flash(
                "Expected attendance must be a valid number.",
                "error"
            )
            return render_template("event_form.html")

        if expected_attendance <= 0:
            flash(
                "Expected attendance must be greater than zero.",
                "error"
            )
            return render_template("event_form.html")

        # ------------------------------------------
        # Validate dates
        # ------------------------------------------

        try:
            start_dt = datetime.fromisoformat(start_value)
            end_dt = datetime.fromisoformat(end_value)

        except ValueError:
            flash(
                "Please enter valid start and end dates.",
                "error"
            )
            return render_template("event_form.html")

        # End must be after start
        if end_dt <= start_dt:
            flash(
                "End time must be after start time.",
                "error"
            )
            return render_template("event_form.html")

        # ------------------------------------------
        # Create Event
        # ------------------------------------------

        event = Event(
            name=name,
            organizer=organizer,
            expected_attendance=expected_attendance,
            start_dt=start_dt,
            end_dt=end_dt,
            status=EventStatus.DRAFT
        )

        db.session.add(event)
        db.session.commit()

        # ------------------------------------------
        # Success
        # ------------------------------------------

        flash(
            "Event created successfully.",
            "success"
        )

        return redirect(
            url_for("events.events")
        )

    # GET request
    return render_template("event_form.html")