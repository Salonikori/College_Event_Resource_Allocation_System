from collections import Counter

from flask import Blueprint, render_template
from flask_login import current_user

from app.models import (
    Allocation,
    AllocationStatus,
    Event,
    Resource,
    ResourceRequest,
    RequestStatus,
    WaitlistEntry,
    WaitlistStatus,
)


dashboard_bp = Blueprint("dashboard", __name__)


def _scoped_event_ids():
    """Return the event IDs visible to the current user."""
    if current_user.is_admin():
        return None
    return [event_id for (event_id,) in Event.query.with_entities(Event.id).filter(
        Event.organizer_id == current_user.id
    ).all()]


@dashboard_bp.route("/")
def dashboard():
    event_ids = _scoped_event_ids()

    event_query = Event.query
    request_query = ResourceRequest.query
    allocation_query = Allocation.query.filter(
        Allocation.status.in_([
            AllocationStatus.ALLOCATED,
            AllocationStatus.APPROVED,
        ])
    )
    waitlist_query = WaitlistEntry.query.filter(
        WaitlistEntry.status == WaitlistStatus.WAITING
    )

    if event_ids is not None:
        event_query = event_query.filter(Event.id.in_(event_ids)) if event_ids else event_query.filter(Event.id == -1)
        request_query = request_query.filter(ResourceRequest.event_id.in_(event_ids)) if event_ids else request_query.filter(ResourceRequest.id == -1)
        allocation_query = allocation_query.filter(Allocation.event_id.in_(event_ids)) if event_ids else allocation_query.filter(Allocation.id == -1)
        waitlist_query = waitlist_query.join(ResourceRequest).filter(ResourceRequest.event_id.in_(event_ids)) if event_ids else waitlist_query.filter(WaitlistEntry.id == -1)

    total_events = event_query.count()
    total_resources = Resource.query.filter_by(is_active=True).count()
    pending_requests = request_query.filter(ResourceRequest.status == RequestStatus.PENDING).count()
    total_requests = request_query.count()
    approved_requests = request_query.filter(ResourceRequest.status == RequestStatus.APPROVED).count()
    active_allocations = allocation_query.count()
    waiting_count = waitlist_query.count()

    allocations = allocation_query.all()

    resource_counts = Counter(a.resource.name for a in allocations if a.resource)
    most_booked_labels = list(resource_counts.keys())[:8]
    most_booked_values = [resource_counts[k] for k in most_booked_labels]

    day_counts = Counter(a.start_dt.strftime("%a") for a in allocations)
    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    busiest_days_labels = day_order
    busiest_days_values = [day_counts[d] for d in day_order]

    hour_counts = Counter(a.start_dt.hour for a in allocations)
    busiest_hours = sorted(hour_counts.items(), key=lambda x: (-x[1], x[0]))[:8]
    busiest_time_labels = [f"{h:02d}:00" for h, _ in busiest_hours]
    busiest_time_values = [v for _, v in busiest_hours]

    approval_rate = round((approved_requests / total_requests) * 100, 1) if total_requests else 0

    return render_template(
        "dashboard.html",
        total_events=total_events,
        total_resources=total_resources,
        pending_requests=pending_requests,
        active_allocations=active_allocations,
        most_booked_labels=most_booked_labels,
        most_booked_values=most_booked_values,
        busiest_days_labels=busiest_days_labels,
        busiest_days_values=busiest_days_values,
        busiest_time_labels=busiest_time_labels,
        busiest_time_values=busiest_time_values,
        approval_rate=approval_rate,
        total_requests=total_requests,
        waiting_count=waiting_count,
    )
