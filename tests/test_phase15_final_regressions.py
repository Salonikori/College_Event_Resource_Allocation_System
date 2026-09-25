from datetime import datetime, timedelta

from app import db
from app.models import (
    Allocation,
    AllocationStatus,
    Event,
    EventStatus,
    RequestItem,
    RequestStatus,
    Resource,
    ResourceType,
    WaitlistEntry,
    WaitlistStatus,
)
from tests.auth_helpers import login_as_admin


def _event():
    event = Event(
        name="Final Regression Event",
        organizer="College",
        expected_attendance=100,
        start_dt=datetime(2026, 10, 10, 10, 0),
        end_dt=datetime(2026, 10, 10, 14, 0),
        status=EventStatus.PENDING,
    )
    db.session.add(event)
    db.session.flush()
    return event


def _resource(event, name="Hall A", capacity=200):
    resource = Resource(
        name=name,
        type=ResourceType.HALL,
        capacity=capacity,
        is_active=True,
        buffer_minutes=0,
    )
    db.session.add(resource)
    db.session.flush()
    allocation = Allocation(
        resource_id=resource.id,
        event_id=event.id,
        request_id=1,
        start_dt=event.start_dt,
        end_dt=event.end_dt,
        status=AllocationStatus.ALLOCATED,
    )
    return resource, allocation


def test_event_schedule_cannot_change_with_active_allocation(app, client):
    with app.app_context():
        event = _event()
        request_row = __import__("app.models", fromlist=["ResourceRequest"]).ResourceRequest(
            event_id=event.id,
            requested_start=event.start_dt,
            requested_end=event.end_dt,
            status=RequestStatus.APPROVED,
        )
        db.session.add(request_row)
        db.session.flush()
        resource = Resource(
            name="Hall A",
            type=ResourceType.HALL,
            capacity=200,
            is_active=True,
            buffer_minutes=0,
        )
        db.session.add(resource)
        db.session.flush()
        allocation = Allocation(
            resource_id=resource.id,
            event_id=event.id,
            request_id=request_row.id,
            start_dt=event.start_dt,
            end_dt=event.end_dt,
            status=AllocationStatus.ALLOCATED,
        )
        db.session.add(allocation)
        db.session.commit()
        event_id = event.id

    response = client.post(
        f"/events/{event_id}/edit",
        data={
            "name": "Moved Event",
            "organizer": "College",
            "expected_attendance": "100",
            "start_dt": "2026-10-10T12:00",
            "end_dt": "2026-10-10T14:00",
            "status": "PENDING",
        },
    )
    assert response.status_code == 200

    with app.app_context():
        event = db.session.get(Event, event_id)
        assert event.start_dt == datetime(2026, 10, 10, 10, 0)
        assert event.end_dt == datetime(2026, 10, 10, 14, 0)


def test_rejecting_request_closes_waitlist_entries(app):
    with app.app_context():
        event = _event()
        from app.models import ResourceRequest
        resource_request = ResourceRequest(
            event_id=event.id,
            requested_start=event.start_dt,
            requested_end=event.end_dt,
            status=RequestStatus.PENDING,
        )
        db.session.add(resource_request)
        db.session.flush()
        db.session.add(RequestItem(
            request_id=resource_request.id,
            resource_type=ResourceType.HALL,
            quantity=1,
        ))
        entry = WaitlistEntry(
            request_id=resource_request.id,
            resource_type=ResourceType.HALL,
            status=WaitlistStatus.WAITING,
        )
        db.session.add(entry)
        db.session.commit()
        request_id = resource_request.id

    client = login_as_admin(app)
    response = client.post(
        f"/approvals/{request_id}/reject",
        data={"rejection_reason": "No capacity"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        entry = WaitlistEntry.query.filter_by(request_id=request_id).one()
        assert entry.status == WaitlistStatus.CANCELLED


def test_resource_type_and_capacity_cannot_change_with_active_allocation(app, client):
    with app.app_context():
        event = _event()
        from app.models import ResourceRequest
        resource_request = ResourceRequest(
            event_id=event.id,
            requested_start=event.start_dt,
            requested_end=event.end_dt,
            status=RequestStatus.APPROVED,
        )
        db.session.add(resource_request)
        db.session.flush()
        resource = Resource(
            name="Hall A",
            type=ResourceType.HALL,
            capacity=200,
            is_active=True,
            buffer_minutes=0,
        )
        db.session.add(resource)
        db.session.flush()
        db.session.add(Allocation(
            resource_id=resource.id,
            event_id=event.id,
            request_id=resource_request.id,
            start_dt=event.start_dt,
            end_dt=event.end_dt,
            status=AllocationStatus.ALLOCATED,
        ))
        db.session.commit()
        resource_id = resource.id

    response = client.post(
        f"/resources/{resource_id}/edit",
        data={
            "name": "Hall A Updated",
            "type": ResourceType.CLASSROOM.value,
            "capacity": "50",
            "buffer_minutes": "5",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        resource = db.session.get(Resource, resource_id)
        assert resource.type == ResourceType.HALL
        assert resource.capacity == 200
