from datetime import datetime

import pytest

from app import create_app, db
from app.models import (
    Allocation,
    AllocationStatus,
    Event,
    EventStatus,
    Resource,
    ResourceRequest,
    RequestItem,
    RequestStatus,
    ResourceType,
)
from app.services.alternatives import (
    find_alternatives,
    find_nearby_time_slots,
    get_resource_alternatives,
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


def create_event(
    session,
    attendance=20,
):
    start = datetime(2026, 10, 1, 10, 0)
    end = datetime(2026, 10, 1, 12, 0)

    event = Event(
        name="Alternative Test Event",
        organizer="Test Organizer",
        expected_attendance=attendance,
        start_dt=start,
        end_dt=end,
        status=EventStatus.PENDING,
    )

    session.add(event)
    session.flush()

    return event, start, end


def create_resource(
    session,
    name,
    resource_type,
    capacity=100,
    is_active=True,
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


def create_allocation(
    session,
    resource,
    start,
    end,
):
    event = Event(
        name="Existing Event",
        organizer="Existing Organizer",
        expected_attendance=20,
        start_dt=start,
        end_dt=end,
        status=EventStatus.APPROVED,
    )

    session.add(event)
    session.flush()

    request = ResourceRequest(
        event_id=event.id,
        requested_start=start,
        requested_end=end,
        status=RequestStatus.APPROVED,
    )

    session.add(request)
    session.flush()

    allocation = Allocation(
        resource_id=resource.id,
        event_id=event.id,
        request_id=request.id,
        start_dt=start,
        end_dt=end,
        status=AllocationStatus.ALLOCATED,
    )

    session.add(allocation)
    session.commit()

    return allocation


# ============================================================
# TEST 1
# ============================================================

def test_find_alternatives_returns_available_resource(session):
    event, start, end = create_event(
        session,
        attendance=20,
    )

    resource = create_resource(
        session,
        "Small Hall",
        ResourceType.HALL,
        capacity=30,
    )

    alternatives = find_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    assert len(alternatives) == 1

    assert alternatives[0]["resource"].id == resource.id


# ============================================================
# TEST 2
# ============================================================

def test_find_alternatives_prefers_smallest_suitable_resource(
    session,
):
    event, start, end = create_event(
        session,
        attendance=30,
    )

    large_hall = create_resource(
        session,
        "Large Hall",
        ResourceType.HALL,
        capacity=200,
    )

    small_hall = create_resource(
        session,
        "Small Hall",
        ResourceType.HALL,
        capacity=40,
    )

    alternatives = find_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    assert len(alternatives) == 2

    # Small Hall should be first because:
    #
    # Small Hall:
    # 40 - 30 = 10
    #
    # Large Hall:
    # 200 - 30 = 170

    assert alternatives[0]["resource"].id == small_hall.id

    assert alternatives[1]["resource"].id == large_hall.id


# ============================================================
# TEST 3
# ============================================================

def test_find_alternatives_ignores_inactive_resources(
    session,
):
    event, start, end = create_event(
        session,
        attendance=20,
    )

    active_resource = create_resource(
        session,
        "Active Hall",
        ResourceType.HALL,
        capacity=50,
        is_active=True,
    )

    create_resource(
        session,
        "Inactive Hall",
        ResourceType.HALL,
        capacity=40,
        is_active=False,
    )

    alternatives = find_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    assert len(alternatives) == 1

    assert alternatives[0]["resource"].id == active_resource.id


# ============================================================
# TEST 4
# ============================================================

def test_find_alternatives_ignores_insufficient_capacity(
    session,
):
    event, start, end = create_event(
        session,
        attendance=50,
    )

    suitable_resource = create_resource(
        session,
        "Suitable Hall",
        ResourceType.HALL,
        capacity=60,
    )

    create_resource(
        session,
        "Small Hall",
        ResourceType.HALL,
        capacity=20,
    )

    alternatives = find_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    assert len(alternatives) == 1

    assert alternatives[0]["resource"].id == suitable_resource.id


# ============================================================
# TEST 5
# ============================================================

def test_find_alternatives_ignores_wrong_resource_type(
    session,
):
    event, start, end = create_event(
        session,
        attendance=20,
    )

    hall = create_resource(
        session,
        "Hall",
        ResourceType.HALL,
        capacity=50,
    )

    create_resource(
        session,
        "Projector",
        ResourceType.PROJECTOR,
        capacity=50,
    )

    alternatives = find_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    assert len(alternatives) == 1

    assert alternatives[0]["resource"].id == hall.id


# ============================================================
# TEST 6
# ============================================================

def test_find_alternatives_ignores_conflicting_resource(
    session,
):
    event, start, end = create_event(
        session,
        attendance=20,
    )

    booked_hall = create_resource(
        session,
        "Booked Hall",
        ResourceType.HALL,
        capacity=50,
    )

    available_hall = create_resource(
        session,
        "Available Hall",
        ResourceType.HALL,
        capacity=60,
    )

    # Existing booking:
    #
    # 10:00 - 12:00
    #
    # Requested:
    # 10:00 - 12:00
    #
    # Therefore Booked Hall must be excluded.

    create_allocation(
        session,
        booked_hall,
        start,
        end,
    )

    alternatives = find_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    assert len(alternatives) == 1

    assert (
        alternatives[0]["resource"].id
        == available_hall.id
    )


# ============================================================
# TEST 7
# ============================================================

def test_find_nearby_time_slots_finds_later_slot(
    session,
):
    event, start, end = create_event(
        session,
        attendance=20,
    )

    resource = create_resource(
        session,
        "Hall A",
        ResourceType.HALL,
        capacity=50,
    )

    # Book the requested time:
    #
    # 10:00 - 12:00

    create_allocation(
        session,
        resource,
        start,
        end,
    )

    suggestions = find_nearby_time_slots(
        session=session,
        resource=resource,
        start_dt=start,
        end_dt=end,
        search_minutes=120,
        step_minutes=30,
    )

    assert len(suggestions) > 0

    # The first available suggestion should be
    # the closest available slot.

    assert suggestions[0]["distance_minutes"] == 120


# ============================================================
# TEST 8
# ============================================================

def test_get_resource_alternatives_returns_exact_resources(
    session,
):
    event, start, end = create_event(
        session,
        attendance=20,
    )

    resource = create_resource(
        session,
        "Available Hall",
        ResourceType.HALL,
        capacity=50,
    )

    result = get_resource_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    assert len(result["exact_time"]) == 1

    assert (
        result["exact_time"][0]["resource"].id
        == resource.id
    )

    assert result["nearby_time"] == []


# ============================================================
# TEST 9
# ============================================================

def test_get_resource_alternatives_returns_nearby_slots(
    session,
):
    event, start, end = create_event(
        session,
        attendance=20,
    )

    resource = create_resource(
        session,
        "Busy Hall",
        ResourceType.HALL,
        capacity=50,
    )

    # Occupy requested time.

    create_allocation(
        session,
        resource,
        start,
        end,
    )

    result = get_resource_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    # No resource available at the exact requested time.

    assert result["exact_time"] == []

    # But nearby slots should exist.

    assert len(result["nearby_time"]) > 0


# ============================================================
# TEST 10
# ============================================================

def test_nearby_slots_preserve_event_duration(
    session,
):
    event, start, end = create_event(
        session,
        attendance=20,
    )

    resource = create_resource(
        session,
        "Hall A",
        ResourceType.HALL,
        capacity=50,
    )

    create_allocation(
        session,
        resource,
        start,
        end,
    )

    suggestions = find_nearby_time_slots(
        session=session,
        resource=resource,
        start_dt=start,
        end_dt=end,
        search_minutes=120,
        step_minutes=30,
    )

    original_duration = end - start

    assert len(suggestions) > 0

    for suggestion in suggestions:
        suggested_duration = (
            suggestion["end_dt"]
            - suggestion["start_dt"]
        )

        assert suggested_duration == original_duration