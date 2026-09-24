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


def make_event(session):

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

    session.add(event)
    session.flush()

    return event


def make_resource(
    session,
    name,
    resource_type,
    capacity=300,
):

    resource = Resource(
        name=name,
        type=resource_type,
        capacity=capacity,
        is_active=True,
        buffer_minutes=0,
    )

    session.add(resource)
    session.flush()

    return resource


def make_request(
    session,
    event,
    items,
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
            14,
            0,
        ),

        status=RequestStatus.PENDING,
    )

    session.add(resource_request)

    session.flush()

    for resource_type, quantity in items:

        session.add(
            RequestItem(
                request_id=
                    resource_request.id,

                resource_type=
                    resource_type,

                quantity=
                    quantity,
            )
        )

    session.flush()

    return resource_request


# ============================================================
# ATOMIC FAILURE
# ============================================================

def test_multi_resource_failure_rolls_back_every_allocation(
    session,
):

    event = make_event(
        session
    )

    hall = make_resource(
        session,
        "Auditorium",
        ResourceType.HALL,
        300,
    )

    projector = make_resource(
        session,
        "Projector 1",
        ResourceType.PROJECTOR,
        100,
    )

    microphone = make_resource(
        session,
        "Microphone 1",
        ResourceType.MICROPHONE,
        100,
    )

    # --------------------------------------------------------
    # Existing microphone booking
    # --------------------------------------------------------

    existing_request = ResourceRequest(
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
            14,
            0,
        ),

        status=RequestStatus.PENDING,
    )

    session.add(
        existing_request
    )

    session.flush()

    session.add(
        RequestItem(
            request_id=
                existing_request.id,

            resource_type=
                ResourceType.MICROPHONE,

            quantity=1,
        )
    )

    session.flush()

    session.add(
        Allocation(
            resource_id=
                microphone.id,

            event_id=
                event.id,

            request_id=
                existing_request.id,

            start_dt=
                existing_request.requested_start,

            end_dt=
                existing_request.requested_end,

            status=
                AllocationStatus.ALLOCATED,
        )
    )

    session.commit()

    # --------------------------------------------------------
    # New request
    # --------------------------------------------------------

    resource_request = make_request(
        session,
        event,
        [
            (
                ResourceType.HALL,
                1,
            ),

            (
                ResourceType.PROJECTOR,
                1,
            ),

            (
                ResourceType.MICROPHONE,
                1,
            ),
        ],
    )

    session.commit()

    # --------------------------------------------------------
    # Approval/allocation should fail
    # --------------------------------------------------------

    with pytest.raises(
        AllocationError
    ):

        allocate_request(
            session,
            resource_request,
            commit=False,
        )

    # --------------------------------------------------------
    # Only old booking remains
    # --------------------------------------------------------

    allocations = (
        Allocation.query
        .order_by(
            Allocation.id.asc()
        )
        .all()
    )

    assert len(
        allocations
    ) == 1

    assert (
        allocations[0].resource_id
        == microphone.id
    )

    # --------------------------------------------------------
    # New request got ZERO allocations
    # --------------------------------------------------------

    request_allocations = (
        Allocation.query
        .filter_by(
            request_id=
                resource_request.id
        )
        .all()
    )

    assert request_allocations == []


# ============================================================
# ATOMIC SUCCESS
# ============================================================

def test_multi_resource_success_creates_all_allocations(
    session,
):

    event = make_event(
        session
    )

    make_resource(
        session,
        "Auditorium",
        ResourceType.HALL,
        300,
    )

    make_resource(
        session,
        "Projector 1",
        ResourceType.PROJECTOR,
        100,
    )

    make_resource(
        session,
        "Microphone 1",
        ResourceType.MICROPHONE,
        100,
    )

    resource_request = make_request(
        session,
        event,
        [
            (
                ResourceType.HALL,
                1,
            ),

            (
                ResourceType.PROJECTOR,
                1,
            ),

            (
                ResourceType.MICROPHONE,
                1,
            ),
        ],
    )

    session.commit()

    allocations = allocate_request(
        session,
        resource_request,
        commit=False,
    )

    assert len(
        allocations
    ) == 3

    assert len(
        Allocation.query
        .filter_by(
            request_id=
                resource_request.id
        )
        .all()
    ) == 3

    session.commit()


# ============================================================
# UI ATOMICITY
# ============================================================

def test_approval_failure_does_not_create_partial_allocations(
    app,
):

    with app.app_context():

        event = make_event(
            db.session
        )

        make_resource(
            db.session,
            "Auditorium",
            ResourceType.HALL,
            300,
        )

        make_resource(
            db.session,
            "Projector 1",
            ResourceType.PROJECTOR,
            100,
        )

        microphone = make_resource(
            db.session,
            "Microphone 1",
            ResourceType.MICROPHONE,
            100,
        )

        # ----------------------------------------------------
        # Existing booking
        # ----------------------------------------------------

        blocker = ResourceRequest(
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
                14,
                0,
            ),

            status=RequestStatus.PENDING,
        )

        db.session.add(
            blocker
        )

        db.session.flush()

        db.session.add(
            Allocation(
                resource_id=
                    microphone.id,

                event_id=
                    event.id,

                request_id=
                    blocker.id,

                start_dt=
                    blocker.requested_start,

                end_dt=
                    blocker.requested_end,

                status=
                    AllocationStatus.ALLOCATED,
            )
        )

        # ----------------------------------------------------
        # Target request
        # ----------------------------------------------------

        target = ResourceRequest(
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
                14,
                0,
            ),

            status=RequestStatus.PENDING,
        )

        db.session.add(
            target
        )

        db.session.flush()

        for resource_type in (
            ResourceType.HALL,
            ResourceType.PROJECTOR,
            ResourceType.MICROPHONE,
        ):

            db.session.add(
                RequestItem(
                    request_id=
                        target.id,

                    resource_type=
                        resource_type,

                    quantity=1,
                )
            )

        db.session.commit()

        target_id = target.id

    client = app.test_client()

    response = client.post(
        f"/approvals/{target_id}/approve",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        target = db.session.get(
            ResourceRequest,
            target_id,
        )

        assert (
            target.status
            == RequestStatus.PENDING
        )

        target_allocations = (
            Allocation.query
            .filter_by(
                request_id=
                    target_id
            )
            .all()
        )

        assert target_allocations == []