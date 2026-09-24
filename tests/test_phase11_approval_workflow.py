from datetime import datetime, timedelta

import pytest

from app import db
from app.models import (
    Allocation,
    AllocationStatus,
    Event,
    EventStatus,
    RequestItem,
    RequestStatus,
    Resource,
    ResourceRequest,
    ResourceType,
)


# ============================================================
# HELPERS
# ============================================================

def create_event(
    app,
    status=EventStatus.PENDING,
):

    with app.app_context():

        event = Event(
            name="Technical Workshop",
            organizer="College",
            expected_attendance=100,
            start_dt=datetime(2026, 10, 10, 10, 0),
            end_dt=datetime(2026, 10, 10, 14, 0),
            status=status,
        )

        db.session.add(event)
        db.session.commit()

        return event.id


def create_resource(
    app,
    resource_type=ResourceType.HALL,
    capacity=200,
):

    with app.app_context():

        resource = Resource(
            name="Hall A",
            type=resource_type,
            capacity=capacity,
            is_active=True,
            buffer_minutes=0,
        )

        db.session.add(resource)
        db.session.commit()

        return resource.id


def create_request(
    app,
    event_id,
    resource_type=ResourceType.HALL,
    quantity=1,
    status=RequestStatus.PENDING,
):

    with app.app_context():

        resource_request = ResourceRequest(
            event_id=event_id,
            requested_start=datetime(
                2026,
                10,
                10,
                10,
                0
            ),
            requested_end=datetime(
                2026,
                10,
                10,
                12,
                0
            ),
            status=status,
        )

        db.session.add(resource_request)

        db.session.flush()

        item = RequestItem(
            request_id=resource_request.id,
            resource_type=resource_type,
            quantity=quantity,
        )

        db.session.add(item)

        db.session.commit()

        return resource_request.id


# ============================================================
# APPROVAL
# ============================================================

def test_pending_request_is_approved_and_allocated(app):

    event_id = create_event(app)

    create_resource(
        app,
        ResourceType.HALL,
        200
    )

    request_id = create_request(
        app,
        event_id
    )

    client = app.test_client()

    response = client.post(
        f"/approvals/{request_id}/approve",
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.app_context():

        resource_request = db.session.get(
            ResourceRequest,
            request_id
        )

        assert (
            resource_request.status
            == RequestStatus.APPROVED
        )

        allocations = (
            Allocation.query
            .filter_by(
                request_id=request_id
            )
            .all()
        )

        assert len(allocations) == 1

        assert (
            allocations[0].status
            == AllocationStatus.ALLOCATED
        )


# ============================================================
# REJECTION
# ============================================================

def test_pending_request_can_be_rejected(app):

    event_id = create_event(app)

    request_id = create_request(
        app,
        event_id
    )

    client = app.test_client()

    response = client.post(
        f"/approvals/{request_id}/reject",
        data={
            "rejection_reason":
                "Requested resource is not available."
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.app_context():

        resource_request = db.session.get(
            ResourceRequest,
            request_id
        )

        assert (
            resource_request.status
            == RequestStatus.REJECTED
        )

        assert (
            resource_request.rejection_reason
            == "Requested resource is not available."
        )


def test_rejection_requires_reason(app):

    event_id = create_event(app)

    request_id = create_request(
        app,
        event_id
    )

    client = app.test_client()

    response = client.post(
        f"/approvals/{request_id}/reject",
        data={
            "rejection_reason": ""
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.app_context():

        resource_request = db.session.get(
            ResourceRequest,
            request_id
        )

        assert (
            resource_request.status
            == RequestStatus.PENDING
        )


# ============================================================
# REJECTED CANNOT BE APPROVED
# ============================================================

def test_rejected_request_cannot_be_approved(app):

    event_id = create_event(app)

    create_resource(
        app,
        ResourceType.HALL,
        200
    )

    request_id = create_request(
        app,
        event_id,
        status=RequestStatus.REJECTED
    )

    client = app.test_client()

    response = client.post(
        f"/approvals/{request_id}/approve",
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.app_context():

        resource_request = db.session.get(
            ResourceRequest,
            request_id
        )

        assert (
            resource_request.status
            == RequestStatus.REJECTED
        )

        assert (
            Allocation.query
            .filter_by(request_id=request_id)
            .count()
            == 0
        )


# ============================================================
# CANCELLED REQUEST CANNOT BE APPROVED
# ============================================================

def test_cancelled_request_cannot_be_approved(app):

    event_id = create_event(app)

    create_resource(
        app,
        ResourceType.HALL,
        200
    )

    request_id = create_request(
        app,
        event_id,
        status=RequestStatus.CANCELLED
    )

    client = app.test_client()

    response = client.post(
        f"/approvals/{request_id}/approve",
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.app_context():

        resource_request = db.session.get(
            ResourceRequest,
            request_id
        )

        assert (
            resource_request.status
            == RequestStatus.CANCELLED
        )

        assert (
            Allocation.query
            .filter_by(request_id=request_id)
            .count()
            == 0
        )


# ============================================================
# CANCELLED EVENT CANNOT BE ALLOCATED
# ============================================================

def test_cancelled_event_cannot_be_approved(app):

    event_id = create_event(
        app,
        status=EventStatus.CANCELLED
    )

    create_resource(
        app,
        ResourceType.HALL,
        200
    )

    request_id = create_request(
        app,
        event_id
    )

    client = app.test_client()

    response = client.post(
        f"/approvals/{request_id}/approve",
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.app_context():

        resource_request = db.session.get(
            ResourceRequest,
            request_id
        )

        assert (
            resource_request.status
            == RequestStatus.PENDING
        )

        assert (
            Allocation.query
            .filter_by(request_id=request_id)
            .count()
            == 0
        )


# ============================================================
# INVALID QUANTITY
# ============================================================

def test_invalid_quantity_cannot_be_approved(app):

    event_id = create_event(app)

    create_resource(
        app,
        ResourceType.HALL,
        200
    )

    request_id = create_request(
        app,
        event_id,
        quantity=0
    )

    client = app.test_client()

    response = client.post(
        f"/approvals/{request_id}/approve",
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.app_context():

        resource_request = db.session.get(
            ResourceRequest,
            request_id
        )

        assert (
            resource_request.status
            == RequestStatus.PENDING
        )

        assert (
            Allocation.query
            .filter_by(request_id=request_id)
            .count()
            == 0
        )


# ============================================================
# UNAVAILABLE RESOURCE
# ============================================================

def test_unavailable_resource_keeps_request_pending(app):

    event_id = create_event(app)

    resource_id = create_resource(
        app,
        ResourceType.HALL,
        200
    )

    # Existing allocation
    with app.app_context():

        existing_request = ResourceRequest(
            event_id=event_id,
            requested_start=datetime(
                2026,
                10,
                10,
                10,
                0
            ),
            requested_end=datetime(
                2026,
                10,
                10,
                12,
                0
            ),
            status=RequestStatus.APPROVED,
        )

        db.session.add(existing_request)

        db.session.flush()

        existing_allocation = Allocation(
            resource_id=resource_id,
            event_id=event_id,
            request_id=existing_request.id,
            start_dt=existing_request.requested_start,
            end_dt=existing_request.requested_end,
            status=AllocationStatus.ALLOCATED,
        )

        db.session.add(existing_allocation)

        db.session.commit()

    request_id = create_request(
        app,
        event_id
    )

    client = app.test_client()

    response = client.post(
        f"/approvals/{request_id}/approve",
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.app_context():

        resource_request = db.session.get(
            ResourceRequest,
            request_id
        )

        assert (
            resource_request.status
            == RequestStatus.PENDING
        )


# ============================================================
# MULTI RESOURCE APPROVAL
# ============================================================

def test_multiple_resources_are_allocated(app):

    event_id = create_event(app)

    hall_id = create_resource(
        app,
        ResourceType.HALL,
        200
    )

    projector_id = create_resource(
        app,
        ResourceType.PROJECTOR,
        1
    )

    with app.app_context():

        resource_request = ResourceRequest(
            event_id=event_id,
            requested_start=datetime(
                2026,
                10,
                10,
                10,
                0
            ),
            requested_end=datetime(
                2026,
                10,
                10,
                12,
                0
            ),
            status=RequestStatus.PENDING,
        )

        db.session.add(resource_request)

        db.session.flush()

        db.session.add(
            RequestItem(
                request_id=resource_request.id,
                resource_type=ResourceType.HALL,
                quantity=1,
            )
        )

        db.session.add(
            RequestItem(
                request_id=resource_request.id,
                resource_type=ResourceType.PROJECTOR,
                quantity=1,
            )
        )

        db.session.commit()

        request_id = resource_request.id

    client = app.test_client()

    response = client.post(
        f"/approvals/{request_id}/approve",
        follow_redirects=True
    )

    assert response.status_code == 200

    with app.app_context():

        resource_request = db.session.get(
            ResourceRequest,
            request_id
        )

        assert (
            resource_request.status
            == RequestStatus.APPROVED
        )

        allocations = (
            Allocation.query
            .filter_by(request_id=request_id)
            .all()
        )

        assert len(allocations) == 2

        allocated_resource_ids = {
            allocation.resource_id
            for allocation in allocations
        }

        assert hall_id in allocated_resource_ids
        assert projector_id in allocated_resource_ids