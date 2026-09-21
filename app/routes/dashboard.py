from flask import Blueprint, render_template

from app.models import Event, Resource, ResourceRequest, Allocation


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
)


@dashboard_bp.route("/")
def dashboard():
    # Total number of events
    total_events = Event.query.count()

    # Total active resources
    total_resources = Resource.query.filter_by(
        is_active=True
    ).count()

    # Requests waiting for approval
    pending_requests = ResourceRequest.query.filter_by(
        status="PENDING"
    ).count()

    # Currently active allocations
    active_allocations = Allocation.query.filter(
        Allocation.status.in_([
            "ALLOCATED",
            "APPROVED"
        ])
    ).count()

    return render_template(
        "dashboard.html",
        total_events=total_events,
        total_resources=total_resources,
        pending_requests=pending_requests,
        active_allocations=active_allocations,
    )