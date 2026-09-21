from flask import Blueprint, render_template

from app.models import Event


events_bp = Blueprint(
    "events",
    __name__,
    url_prefix="/events",
)


@events_bp.route("/")
def events():
    events = Event.query.order_by(
        Event.start_dt.asc()
    ).all()

    return render_template(
        "events.html",
        events=events,
    )