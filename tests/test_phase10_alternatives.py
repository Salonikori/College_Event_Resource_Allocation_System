from datetime import datetime

from app.models import (
    Allocation,
    AllocationStatus,
    Event,
    EventStatus,
    RequestStatus,
    Resource,
    ResourceRequest,
    ResourceType,
)

from app.services.alternatives import (
    find_alternatives,
    find_nearby_time_slots,
    get_resource_alternatives,
)


# ============================================================
# HELPERS
# ============================================================

def create_event(
    session,
    attendance=50,
):

    start = datetime(
        2026,
        10,
        1,
        10,
        0,
    )

    end = datetime(
        2026,
        10,
        1,
        12,
        0,
    )

    event = Event(
        name="Technical Workshop",
        organizer="College",
        expected_attendance=attendance,
        start_dt=start,
        end_dt=end,
        status=EventStatus.APPROVED,
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
    buffer_minutes=0,
):

    resource = Resource(
        name=name,
        type=resource_type,
        capacity=capacity,
        is_active=is_active,
        buffer_minutes=buffer_minutes,
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
        organizer="College",
        expected_attendance=20,
        start_dt=start,
        end_dt=end,
        status=EventStatus.APPROVED,
    )

    session.add(event)
    session.flush()

    resource_request = ResourceRequest(
        event_id=event.id,
        requested_start=start,
        requested_end=end,
        status=RequestStatus.APPROVED,
    )

    session.add(resource_request)
    session.flush()

    allocation = Allocation(
        resource_id=resource.id,
        event_id=event.id,
        request_id=resource_request.id,
        start_dt=start,
        end_dt=end,
        status=AllocationStatus.ALLOCATED,
    )

    session.add(allocation)
    session.commit()

    return allocation


# ============================================================
# TEST 1
# Available alternative
# ============================================================

def test_available_resource_is_returned(session):

    event, start, end = create_event(
        session,
        attendance=20,
    )

    hall = create_resource(
        session,
        "Hall B",
        ResourceType.HALL,
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

    assert (
        alternatives[0]["resource"].id
        == hall.id
    )


# ============================================================
# TEST 2
# Requested resource is excluded
# ============================================================

def test_requested_resource_is_excluded(session):

    event, start, end = create_event(
        session,
        attendance=20,
    )

    hall_a = create_resource(
        session,
        "Hall A",
        ResourceType.HALL,
        capacity=100,
    )

    hall_b = create_resource(
        session,
        "Hall B",
        ResourceType.HALL,
        capacity=150,
    )

    alternatives = find_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
        excluded_resource_id=hall_a.id,
    )

    resource_ids = [
        candidate["resource"].id
        for candidate in alternatives
    ]

    assert hall_a.id not in resource_ids

    assert hall_b.id in resource_ids


# ============================================================
# TEST 3
# Wrong resource type excluded
# ============================================================

def test_wrong_resource_type_excluded(session):

    event, start, end = create_event(
        session,
        attendance=20,
    )

    hall = create_resource(
        session,
        "Hall",
        ResourceType.HALL,
        capacity=100,
    )

    create_resource(
        session,
        "Projector",
        ResourceType.PROJECTOR,
        capacity=100,
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
        == hall.id
    )


# ============================================================
# TEST 4
# Inactive resources excluded
# ============================================================

def test_inactive_resource_excluded(session):

    event, start, end = create_event(
        session,
        attendance=20,
    )

    active = create_resource(
        session,
        "Active Hall",
        ResourceType.HALL,
        capacity=100,
        is_active=True,
    )

    create_resource(
        session,
        "Inactive Hall",
        ResourceType.HALL,
        capacity=100,
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

    assert (
        alternatives[0]["resource"].id
        == active.id
    )


# ============================================================
# TEST 5
# Insufficient capacity excluded
# ============================================================

def test_insufficient_capacity_excluded(session):

    event, start, end = create_event(
        session,
        attendance=200,
    )

    suitable = create_resource(
        session,
        "Large Hall",
        ResourceType.HALL,
        capacity=300,
    )

    create_resource(
        session,
        "Small Hall",
        ResourceType.HALL,
        capacity=100,
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
        == suitable.id
    )


# ============================================================
# TEST 6
# Conflicting resource excluded
# ============================================================

def test_conflicting_resource_excluded(session):

    event, start, end = create_event(
        session,
        attendance=20,
    )

    booked = create_resource(
        session,
        "Booked Hall",
        ResourceType.HALL,
        capacity=100,
    )

    available = create_resource(
        session,
        "Available Hall",
        ResourceType.HALL,
        capacity=100,
    )

    create_allocation(
        session,
        booked,
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
        == available.id
    )


# ============================================================
# TEST 7
# Buffer time respected
# ============================================================

def test_buffer_time_is_respected(session):

    event, start, end = create_event(
        session,
        attendance=20,
    )

    resource = create_resource(
        session,
        "Hall A",
        ResourceType.HALL,
        capacity=100,
        buffer_minutes=30,
    )

    existing_start = datetime(
        2026,
        10,
        1,
        12,
        0,
    )

    existing_end = datetime(
        2026,
        10,
        1,
        14,
        0,
    )

    create_allocation(
        session,
        resource,
        existing_start,
        existing_end,
    )

    # Requested:
    # 14:00 - 16:00
    #
    # Buffer means resource is unavailable until 14:30.

    requested_start = datetime(
        2026,
        10,
        1,
        14,
        0,
    )

    requested_end = datetime(
        2026,
        10,
        1,
        16,
        0,
    )

    alternatives = find_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=requested_start,
        end_dt=requested_end,
    )

    assert alternatives == []


# ============================================================
# TEST 8
# Best-fit resource first
# ============================================================

def test_best_fit_resource_first(session):

    event, start, end = create_event(
        session,
        attendance=50,
    )

    large = create_resource(
        session,
        "Large Hall",
        ResourceType.HALL,
        capacity=500,
    )

    small = create_resource(
        session,
        "Small Hall",
        ResourceType.HALL,
        capacity=75,
    )

    alternatives = find_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    assert len(alternatives) == 2

    assert (
        alternatives[0]["resource"].id
        == small.id
    )

    assert (
        alternatives[1]["resource"].id
        == large.id
    )


# ============================================================
# TEST 9
# Reason is generated
# ============================================================

def test_alternative_contains_reason(session):

    event, start, end = create_event(
        session,
        attendance=50,
    )

    hall = create_resource(
        session,
        "Hall B",
        ResourceType.HALL,
        capacity=100,
        buffer_minutes=15,
    )

    alternatives = find_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    assert len(alternatives) == 1

    reason = alternatives[0]["reason"]

    assert "Hall B" in reason
    assert "100" in reason
    assert "15" in reason


# ============================================================
# TEST 10
# Nearby time slot
# ============================================================

def test_nearby_time_slot(session):

    event, start, end = create_event(
        session,
        attendance=20,
    )

    resource = create_resource(
        session,
        "Hall A",
        ResourceType.HALL,
        capacity=100,
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
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
        search_minutes=120,
        step_minutes=30,
    )

    assert len(suggestions) > 0


# ============================================================
# TEST 11
# Nearby slot preserves duration
# ============================================================

def test_nearby_slot_preserves_duration(session):

    event, start, end = create_event(
        session,
        attendance=20,
    )

    resource = create_resource(
        session,
        "Hall A",
        ResourceType.HALL,
        capacity=100,
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
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
        search_minutes=120,
        step_minutes=30,
    )

    original_duration = end - start

    for suggestion in suggestions:

        duration = (
            suggestion["end_dt"]
            - suggestion["start_dt"]
        )

        assert duration == original_duration


# ============================================================
# TEST 12
# get_resource_alternatives exact result
# ============================================================

def test_get_resource_alternatives_exact_time(session):

    event, start, end = create_event(
        session,
        attendance=20,
    )

    hall_a = create_resource(
        session,
        "Hall A",
        ResourceType.HALL,
        capacity=100,
    )

    hall_b = create_resource(
        session,
        "Hall B",
        ResourceType.HALL,
        capacity=150,
    )

    result = get_resource_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
        excluded_resource_id=hall_a.id,
    )

    assert len(result["exact_time"]) == 1

    assert (
        result["exact_time"][0]["resource"].id
        == hall_b.id
    )

    assert result["nearby_time"] == []


# ============================================================
# TEST 13
# Requested resource excluded from nearby slots
# ============================================================

def test_requested_resource_excluded_from_nearby_slots(
    session,
):

    event, start, end = create_event(
        session,
        attendance=20,
    )

    hall_a = create_resource(
        session,
        "Hall A",
        ResourceType.HALL,
        capacity=100,
    )

    hall_b = create_resource(
        session,
        "Hall B",
        ResourceType.HALL,
        capacity=100,
    )

    create_allocation(
        session,
        hall_a,
        start,
        end,
    )

    result = get_resource_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
        excluded_resource_id=hall_a.id,
    )

    for slot in result["nearby_time"]:

        assert (
            slot["resource"].id
            != hall_a.id
        )


# ============================================================
# TEST 14
# No suitable alternative
# ============================================================

def test_no_suitable_alternative(session):

    event, start, end = create_event(
        session,
        attendance=500,
    )

    create_resource(
        session,
        "Small Hall",
        ResourceType.HALL,
        capacity=100,
    )

    result = get_resource_alternatives(
        session=session,
        event=event,
        required_type=ResourceType.HALL,
        start_dt=start,
        end_dt=end,
    )

    assert result["exact_time"] == []
    assert result["nearby_time"] == []