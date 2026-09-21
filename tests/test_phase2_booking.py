from datetime import datetime

from app import create_app, db
from app.models import (
    Event,
    Resource,
    ResourceRequest,
    Allocation,
    ResourceType,
    AllocationStatus
)
from app.services.booking import find_conflicts


def create_test_data():
    """
    Creates one event, one resource,
    one request and one allocation.
    """

    event = Event(
        name="Test Event",
        organizer="Test Organizer",
        expected_attendance=100,
        start_dt=datetime(2026, 10, 10, 10, 0),
        end_dt=datetime(2026, 10, 10, 14, 0)
    )

    resource = Resource(
        name="Test Hall",
        type=ResourceType.HALL,
        capacity=200,
        is_active=True
    )

    db.session.add(event)
    db.session.add(resource)

    db.session.commit()

    request = ResourceRequest(
        event_id=event.id,
        requested_start=datetime(2026, 10, 10, 10, 0),
        requested_end=datetime(2026, 10, 10, 14, 0)
    )

    db.session.add(request)
    db.session.commit()

    allocation = Allocation(
        resource_id=resource.id,
        event_id=event.id,
        request_id=request.id,
        start_dt=datetime(2026, 10, 10, 10, 0),
        end_dt=datetime(2026, 10, 10, 14, 0),
        status=AllocationStatus.ALLOCATED
    )

    db.session.add(allocation)
    db.session.commit()

    return resource, allocation


def setup_database():
    app = create_app()

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    return app


def test_overlapping_booking():
    """
    10:00-14:00 existing
    12:00-16:00 new

    Expected: CONFLICT
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        resource, allocation = create_test_data()

        conflicts = find_conflicts(
            db.session,
            resource.id,
            datetime(2026, 10, 10, 12, 0),
            datetime(2026, 10, 10, 16, 0)
        )

        assert len(conflicts) == 1
        assert conflicts[0].id == allocation.id


def test_non_overlapping_booking():
    """
    10:00-14:00 existing
    14:00-16:00 new

    Expected: NO CONFLICT
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        resource, allocation = create_test_data()

        conflicts = find_conflicts(
            db.session,
            resource.id,
            datetime(2026, 10, 10, 14, 0),
            datetime(2026, 10, 10, 16, 0)
        )

        assert len(conflicts) == 0


def test_cancelled_allocation_does_not_conflict():
    """
    Cancelled allocations should not block
    the resource.
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        resource, allocation = create_test_data()

        allocation.status = AllocationStatus.CANCELLED

        db.session.commit()

        conflicts = find_conflicts(
            db.session,
            resource.id,
            datetime(2026, 10, 10, 12, 0),
            datetime(2026, 10, 10, 16, 0)
        )

        assert len(conflicts) == 0


def test_exclude_existing_allocation():
    """
    When editing an existing allocation,
    it should not conflict with itself.
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        resource, allocation = create_test_data()

        conflicts = find_conflicts(
            db.session,
            resource.id,
            datetime(2026, 10, 10, 10, 0),
            datetime(2026, 10, 10, 14, 0),
            exclude_alloc_id=allocation.id
        )

        assert len(conflicts) == 0

def test_different_resource_does_not_conflict():
    """
    An allocation on Resource A must not conflict
    with a booking on Resource B.
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        resource, allocation = create_test_data()

        another_resource = Resource(
            name="Second Hall",
            type=ResourceType.HALL,
            capacity=200,
            is_active=True
        )

        db.session.add(another_resource)
        db.session.commit()

        conflicts = find_conflicts(
            db.session,
            another_resource.id,
            datetime(2026, 10, 10, 12, 0),
            datetime(2026, 10, 10, 16, 0)
        )

        assert len(conflicts) == 0


def test_exact_boundary_is_not_conflict():
    """
    Existing: 10:00-14:00
    New:      14:00-18:00

    Because the intervals only touch at 14:00,
    there should be no conflict.
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        resource, allocation = create_test_data()

        conflicts = find_conflicts(
            db.session,
            resource.id,
            datetime(2026, 10, 10, 14, 0),
            datetime(2026, 10, 10, 18, 0)
        )

        assert len(conflicts) == 0