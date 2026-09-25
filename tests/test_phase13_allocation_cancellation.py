from datetime import datetime

import pytest

from tests.auth_helpers import login_as_admin
from app import create_app, db

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

from app.services.booking import (
    allocate_request,
    find_conflicts,
)


@pytest.fixture
def app():

    app = create_app()

    with app.app_context():

        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


def create_event():

    event = Event(
        name="Technical Workshop",
        organizer="College",
        expected_attendance=100,

        start_dt=datetime(
            2026,
            10,
            10,
            10,
            0,
        ),

        end_dt=datetime(
            2026,
            10,
            10,
            14,
            0,
        ),

        status=EventStatus.PENDING,
    )

    db.session.add(
        event
    )

    db.session.flush()

    return event


def create_resource():

    resource = Resource(
        name="Projector 1",
        type=ResourceType.PROJECTOR,
        capacity=100,
        is_active=True,
        buffer_minutes=0,
    )

    db.session.add(
        resource
    )

    db.session.flush()

    return resource


def create_request(
    event,
):

    resource_request = ResourceRequest(
        event_id=event.id,

        requested_start=datetime(
            2026,
            10,
            10,
            10,
            0,
        ),

        requested_end=datetime(
            2026,
            10,
            10,
            12,
            0,
        ),

        status=RequestStatus.PENDING,
    )

    db.session.add(
        resource_request
    )

    db.session.flush()

    db.session.add(
        RequestItem(
            request_id=
                resource_request.id,

            resource_type=
                ResourceType.PROJECTOR,

            quantity=1,
        )
    )

    db.session.flush()

    return resource_request


# ============================================================
# CANCEL PRESERVES HISTORY
# ============================================================

def test_cancel_allocation_keeps_history(
    app,
):

    with app.app_context():

        event = create_event()

        resource = create_resource()

        resource_request = create_request(
            event
        )

        allocation = Allocation(
            resource_id=
                resource.id,

            event_id=
                event.id,

            request_id=
                resource_request.id,

            start_dt=
                resource_request.requested_start,

            end_dt=
                resource_request.requested_end,

            status=
                AllocationStatus.ALLOCATED,
        )

        db.session.add(
            allocation
        )

        db.session.commit()

        allocation_id = allocation.id

    client = login_as_admin(app)

    response = client.post(
        (
            "/approvals/allocations/"
            f"{allocation_id}/cancel"
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        saved = db.session.get(
            Allocation,
            allocation_id,
        )

        assert saved is not None

        assert (
            saved.status
            == AllocationStatus.CANCELLED
        )


# ============================================================
# CANCELLED DOES NOT CONFLICT
# ============================================================

def test_cancelled_allocation_no_longer_blocks_resource(
    app,
):

    with app.app_context():

        event = create_event()

        resource = create_resource()

        resource_request = create_request(
            event
        )

        allocation = Allocation(
            resource_id=
                resource.id,

            event_id=
                event.id,

            request_id=
                resource_request.id,

            start_dt=
                resource_request.requested_start,

            end_dt=
                resource_request.requested_end,

            status=
                AllocationStatus.ALLOCATED,
        )

        db.session.add(
            allocation
        )

        db.session.commit()

        # Cancel it manually.
        allocation.status = (
            AllocationStatus.CANCELLED
        )

        db.session.commit()

        conflicts = find_conflicts(
            db.session,

            resource.id,

            datetime(
                2026,
                10,
                10,
                10,
                0,
            ),

            datetime(
                2026,
                10,
                10,
                12,
                0,
            ),
        )

        assert conflicts == []


# ============================================================
# NEW BOOKING AFTER CANCELLATION
# ============================================================

def test_new_booking_can_use_cancelled_resource(
    app,
):

    with app.app_context():

        event = create_event()

        resource = create_resource()

        old_request = create_request(
            event
        )

        old_allocation = Allocation(
            resource_id=
                resource.id,

            event_id=
                event.id,

            request_id=
                old_request.id,

            start_dt=
                old_request.requested_start,

            end_dt=
                old_request.requested_end,

            status=
                AllocationStatus.CANCELLED,
        )

        db.session.add(
            old_allocation
        )

        new_request = create_request(
            event
        )

        db.session.commit()

        allocations = allocate_request(
            db.session,
            new_request,
        )

        assert len(
            allocations
        ) == 1

        assert (
            allocations[0].resource_id
            == resource.id
        )

        assert (
            allocations[0].status
            == AllocationStatus.ALLOCATED
        )


# ============================================================
# ROUTE DOES NOT DELETE
# ============================================================

def test_cancel_route_does_not_delete_allocation(
    app,
):

    with app.app_context():

        event = create_event()

        resource = create_resource()

        resource_request = create_request(
            event
        )

        allocation = Allocation(
            resource_id=
                resource.id,

            event_id=
                event.id,

            request_id=
                resource_request.id,

            start_dt=
                resource_request.requested_start,

            end_dt=
                resource_request.requested_end,

            status=
                AllocationStatus.APPROVED,
        )

        db.session.add(
            allocation
        )

        db.session.commit()

        allocation_id = allocation.id

    client = login_as_admin(app)

    response = client.post(
        (
            "/approvals/allocations/"
            f"{allocation_id}/cancel"
        )
    )

    assert response.status_code == 302

    with app.app_context():

        saved = db.session.get(
            Allocation,
            allocation_id,
        )

        assert saved is not None

        assert (
            saved.status
            == AllocationStatus.CANCELLED
        )