from datetime import datetime

import pytest

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
    AllocationError,
    allocate_request,
)


@pytest.fixture
def app():
    app = create_app()

    with app.app_context():
        db.drop_all()
        db.create_all()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def session(app):
    with app.app_context():
        yield db.session


def create_request(
    session,
    resource_type,
    quantity=1
):
    start = datetime(2026, 10, 1, 10, 0)
    end = datetime(2026, 10, 1, 12, 0)

    event = Event(
        name="Test Event",
        organizer="Test Organizer",
        expected_attendance=20,
        start_dt=start,
        end_dt=end,
        status=EventStatus.PENDING,
    )

    session.add(event)
    session.flush()

    request = ResourceRequest(
        event_id=event.id,
        requested_start=start,
        requested_end=end,
        status=RequestStatus.PENDING,
    )

    session.add(request)
    session.flush()

    item = RequestItem(
        request_id=request.id,
        resource_type=resource_type,
        quantity=quantity,
    )

    session.add(item)
    session.flush()

    return request, item


def create_resource(
    session,
    name,
    resource_type,
    capacity=100,
    is_active=True
):
    resource = Resource(
        name=name,
        type=resource_type,
        capacity=capacity,
        is_active=is_active,
        buffer_minutes=0,
    )

    session.add(resource)
    session.flush()

    return resource


def test_allocate_multiple_resources(session):
    request, item = create_request(
        session,
        ResourceType.PROJECTOR,
        quantity=2,
    )

    create_resource(
        session,
        "Projector 1",
        ResourceType.PROJECTOR,
    )

    create_resource(
        session,
        "Projector 2",
        ResourceType.PROJECTOR,
    )

    allocations = allocate_request(
        session,
        request,
    )

    assert len(allocations) == 2

    saved_allocations = session.query(
        Allocation
    ).all()

    assert len(saved_allocations) == 2

    assert all(
        allocation.status == AllocationStatus.ALLOCATED
        for allocation in saved_allocations
    )


def test_allocate_requested_quantity(session):
    request, item = create_request(
        session,
        ResourceType.COMPUTER,
        quantity=3,
    )

    create_resource(
        session,
        "Computer 1",
        ResourceType.COMPUTER,
    )

    create_resource(
        session,
        "Computer 2",
        ResourceType.COMPUTER,
    )

    create_resource(
        session,
        "Computer 3",
        ResourceType.COMPUTER,
    )

    allocations = allocate_request(
        session,
        request,
    )

    assert len(allocations) == 3

    resource_ids = {
        allocation.resource_id
        for allocation in allocations
    }

    assert len(resource_ids) == 3


def test_allocation_fails_when_not_enough_resources(session):
    request, item = create_request(
        session,
        ResourceType.PROJECTOR,
        quantity=2,
    )

    create_resource(
        session,
        "Projector 1",
        ResourceType.PROJECTOR,
    )

    with pytest.raises(AllocationError):
        allocate_request(
            session,
            request,
        )


def test_failed_allocation_creates_nothing(session):
    request, item = create_request(
        session,
        ResourceType.PROJECTOR,
        quantity=2,
    )

    create_resource(
        session,
        "Projector 1",
        ResourceType.PROJECTOR,
    )

    with pytest.raises(AllocationError):
        allocate_request(
            session,
            request,
        )

    allocations = session.query(
        Allocation
    ).all()

    assert len(allocations) == 0


def test_specific_resource_allocation(session):
    request, item = create_request(
        session,
        ResourceType.PROJECTOR,
        quantity=1,
    )

    resource1 = create_resource(
        session,
        "Projector 1",
        ResourceType.PROJECTOR,
    )

    resource2 = create_resource(
        session,
        "Projector 2",
        ResourceType.PROJECTOR,
    )

    item.specific_resource_id = resource2.id

    session.flush()

    allocations = allocate_request(
        session,
        request,
    )

    assert len(allocations) == 1

    assert allocations[0].resource_id == resource2.id

    assert allocations[0].resource_id != resource1.id


def test_already_booked_resource_is_not_selected(session):
    request1, item1 = create_request(
        session,
        ResourceType.PROJECTOR,
        quantity=1,
    )

    resource = create_resource(
        session,
        "Projector 1",
        ResourceType.PROJECTOR,
    )

    first_allocation = Allocation(
        resource_id=resource.id,
        event_id=request1.event_id,
        request_id=request1.id,
        start_dt=request1.requested_start,
        end_dt=request1.requested_end,
        status=AllocationStatus.ALLOCATED,
    )

    session.add(first_allocation)
    session.commit()

    request2, item2 = create_request(
        session,
        ResourceType.PROJECTOR,
        quantity=1,
    )

    with pytest.raises(AllocationError):
        allocate_request(
            session,
            request2,
        )

    allocations = session.query(
        Allocation
    ).all()

    assert len(allocations) == 1


def test_successful_allocation_is_committed(session):
    request, item = create_request(
        session,
        ResourceType.MICROPHONE,
        quantity=1,
    )

    resource = create_resource(
        session,
        "Microphone 1",
        ResourceType.MICROPHONE,
    )

    allocations = allocate_request(
        session,
        request,
    )

    assert len(allocations) == 1

    session.expire_all()

    saved_allocation = session.query(
        Allocation
    ).filter_by(
        resource_id=resource.id
    ).first()

    assert saved_allocation is not None

    assert (
        saved_allocation.status
        == AllocationStatus.ALLOCATED
    )