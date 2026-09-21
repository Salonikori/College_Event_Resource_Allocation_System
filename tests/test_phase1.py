from datetime import datetime

from app import create_app, db
from app.models import (
    Event,
    Resource,
    ResourceRequest,
    RequestItem,
    Allocation,
    ResourceType,
    EventStatus
)


def test_phase1_database():
    app = create_app()

    with app.app_context():

        # Clear existing test data
        db.drop_all()
        db.create_all()

        # --------------------------------------------------
        # 1. Create Event
        # --------------------------------------------------

        event = Event(
            name="College Tech Fest",
            organizer="Computer Department",
            expected_attendance=100,
            start_dt=datetime(2026, 10, 10, 10, 0),
            end_dt=datetime(2026, 10, 10, 14, 0),
            status=EventStatus.DRAFT
        )

        db.session.add(event)
        db.session.commit()

        assert event.id is not None

        # --------------------------------------------------
        # 2. Create Resource
        # --------------------------------------------------

        hall = Resource(
            name="Main Auditorium",
            type=ResourceType.HALL,
            capacity=300,
            is_active=True,
            buffer_minutes=30
        )

        db.session.add(hall)
        db.session.commit()

        assert hall.id is not None

        # --------------------------------------------------
        # 3. Create Resource Request
        # --------------------------------------------------

        request = ResourceRequest(
            event_id=event.id,
            requested_start=datetime(2026, 10, 10, 10, 0),
            requested_end=datetime(2026, 10, 10, 14, 0)
        )

        db.session.add(request)
        db.session.commit()

        assert request.id is not None

        # --------------------------------------------------
        # 4. Create Request Item
        # --------------------------------------------------

        item = RequestItem(
            request_id=request.id,
            resource_type=ResourceType.HALL,
            quantity=1,
            specific_resource_id=hall.id
        )

        db.session.add(item)
        db.session.commit()

        assert item.id is not None

        # --------------------------------------------------
        # 5. Create Allocation
        # --------------------------------------------------

        allocation = Allocation(
            resource_id=hall.id,
            event_id=event.id,
            request_id=request.id,
            start_dt=datetime(2026, 10, 10, 10, 0),
            end_dt=datetime(2026, 10, 10, 14, 0)
        )

        db.session.add(allocation)
        db.session.commit()

        assert allocation.id is not None

        # --------------------------------------------------
        # Verify relationships
        # --------------------------------------------------

        assert event.resource_requests[0].id == request.id

        assert request.items[0].id == item.id

        assert request.allocations[0].id == allocation.id

        assert hall.allocations[0].id == allocation.id

        print("Phase 1 test completed successfully.")