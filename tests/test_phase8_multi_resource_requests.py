
from datetime import datetime

import pytest
from werkzeug.datastructures import MultiDict

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


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def app():
    """
    Create a fresh Flask application for each test.
    """
    app = create_app()

    app.config["TESTING"] = True

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app, admin_user):
    """
    Flask test client, logged in as an admin so existing
    route-level tests keep working now that every page
    requires authentication.
    """
    test_client = app.test_client()

    test_client.post(
        "/auth/login",
        data={
            "email": "test-admin@resourcehub.edu",
            "password": "password123",
        },
    )

    return test_client


@pytest.fixture
def event(app):
    """
    Create the standard Technical Workshop event.
    """

    with app.app_context():

        event = Event(
            name="Technical Workshop",
            organizer="Test Organizer",
            expected_attendance=100,
            start_dt=datetime(
                2026,
                10,
                10,
                9,
                0,
            ),
            end_dt=datetime(
                2026,
                10,
                10,
                17,
                0,
            ),
            status=EventStatus.APPROVED,
        )

        db.session.add(event)
        db.session.commit()

        return event.id


# ============================================================
# HELPER
# ============================================================

def create_resource(
    resource_type,
    name,
    capacity=None,
    buffer_minutes=0,
):
    """
    Create a resource inside the current application context.
    """

    resource = Resource(
        name=name,
        type=resource_type,
        capacity=capacity,
        is_active=True,
        buffer_minutes=buffer_minutes,
    )

    db.session.add(resource)

    return resource


# ============================================================
# 1. ONE RESOURCE REQUEST
# ============================================================

def test_one_resource_request(
    client,
    app,
    event,
):

    with app.app_context():

        create_resource(
            ResourceType.HALL,
            "Auditorium",
            capacity=300,
        )

        db.session.commit()

    response = client.post(
        "/requests/create",
        data={
            "event_id": str(event),
            "requested_start": "2026-10-10T10:00",
            "requested_end": "2026-10-10T14:00",
            "resource_type": "HALL",
            "quantity": "1",
        },
    )

    assert response.status_code in (200, 302)

    with app.app_context():

        resource_request = (
            ResourceRequest.query
            .order_by(ResourceRequest.id.desc())
            .first()
        )

        assert resource_request is not None

        assert resource_request.event_id == event

        assert len(resource_request.items) == 1

        item = resource_request.items[0]

        assert item.resource_type == ResourceType.HALL

        assert item.quantity == 1


# ============================================================
# 2. MULTIPLE RESOURCES
# ============================================================

def test_multiple_resources(
    client,
    app,
    event,
):

    with app.app_context():

        create_resource(
            ResourceType.HALL,
            "Auditorium",
            capacity=300,
        )

        create_resource(
            ResourceType.PROJECTOR,
            "Projector 1",
        )

        create_resource(
            ResourceType.MICROPHONE,
            "Microphone 1",
        )

        create_resource(
            ResourceType.MICROPHONE,
            "Microphone 2",
        )

        db.session.commit()

    response = client.post(
        "/requests/create",
        data=MultiDict(
            [
                (
                    "event_id",
                    str(event),
                ),
                (
                    "requested_start",
                    "2026-10-10T10:00",
                ),
                (
                    "requested_end",
                    "2026-10-10T14:00",
                ),

                (
                    "resource_type",
                    "HALL",
                ),
                (
                    "quantity",
                    "1",
                ),

                (
                    "resource_type",
                    "PROJECTOR",
                ),
                (
                    "quantity",
                    "1",
                ),

                (
                    "resource_type",
                    "MICROPHONE",
                ),
                (
                    "quantity",
                    "2",
                ),
            ]
        ),
    )

    assert response.status_code in (200, 302)

    with app.app_context():

        resource_request = (
            ResourceRequest.query
            .order_by(ResourceRequest.id.desc())
            .first()
        )

        assert resource_request is not None

        assert resource_request.event_id == event

        assert len(resource_request.items) == 3

        items = resource_request.items

        hall_items = [
            item
            for item in items
            if item.resource_type == ResourceType.HALL
        ]

        projector_items = [
            item
            for item in items
            if item.resource_type == ResourceType.PROJECTOR
        ]

        microphone_items = [
            item
            for item in items
            if item.resource_type == ResourceType.MICROPHONE
        ]

        assert len(hall_items) == 1
        assert hall_items[0].quantity == 1

        assert len(projector_items) == 1
        assert projector_items[0].quantity == 1

        assert len(microphone_items) == 1
        assert microphone_items[0].quantity == 2


# ============================================================
# 3. MULTIPLE QUANTITIES
# ============================================================

def test_multiple_quantities(
    client,
    app,
    event,
):

    with app.app_context():

        create_resource(
            ResourceType.MICROPHONE,
            "Microphone 1",
        )

        create_resource(
            ResourceType.MICROPHONE,
            "Microphone 2",
        )

        create_resource(
            ResourceType.MICROPHONE,
            "Microphone 3",
        )

        db.session.commit()

    response = client.post(
        "/requests/create",
        data=MultiDict(
            [
                (
                    "event_id",
                    str(event),
                ),
                (
                    "requested_start",
                    "2026-10-10T10:00",
                ),
                (
                    "requested_end",
                    "2026-10-10T14:00",
                ),
                (
                    "resource_type",
                    "MICROPHONE",
                ),
                (
                    "quantity",
                    "3",
                ),
            ]
        ),
    )

    assert response.status_code in (200, 302)

    with app.app_context():

        resource_request = (
            ResourceRequest.query
            .order_by(ResourceRequest.id.desc())
            .first()
        )

        assert resource_request is not None

        assert len(resource_request.items) == 1

        item = resource_request.items[0]

        assert item.resource_type == ResourceType.MICROPHONE

        assert item.quantity == 3


# ============================================================
# 4. INVALID QUANTITY
# ============================================================

@pytest.mark.parametrize(
    "quantity",
    [
        "0",
        "-1",
        "abc",
        "1.5",
    ],
)
def test_invalid_quantity(
    client,
    app,
    event,
    quantity,
):

    with app.app_context():

        create_resource(
            ResourceType.MICROPHONE,
            "Microphone",
        )

        db.session.commit()

    response = client.post(
        "/requests/create",
        data={
            "event_id": str(event),
            "requested_start": "2026-10-10T10:00",
            "requested_end": "2026-10-10T14:00",
            "resource_type": "MICROPHONE",
            "quantity": quantity,
        },
    )

    assert response.status_code == 400


# ============================================================
# 5. INVALID RESOURCE TYPE
# ============================================================

def test_invalid_resource_type(
    client,
    app,
    event,
):

    response = client.post(
        "/requests/create",
        data={
            "event_id": str(event),
            "requested_start": "2026-10-10T10:00",
            "requested_end": "2026-10-10T14:00",
            "resource_type": "INVALID_RESOURCE",
            "quantity": "1",
        },
    )

    assert response.status_code == 400


# ============================================================
# 6. ONE UNAVAILABLE RESOURCE
# ============================================================

def test_one_unavailable_resource(
    client,
    app,
    event,
):

    with app.app_context():

        resource = create_resource(
            ResourceType.PROJECTOR,
            "Projector 1",
        )

        db.session.commit()

        existing_request = ResourceRequest(
            event_id=event,
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

        db.session.add(existing_request)

        db.session.flush()

        allocation = Allocation(
            resource_id=resource.id,
            event_id=event,
            request_id=existing_request.id,
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
            status=AllocationStatus.ALLOCATED,
        )

        db.session.add(allocation)

        db.session.commit()

    response = client.post(
        "/requests/create",
        data={
            "event_id": str(event),
            "requested_start": "2026-10-10T10:00",
            "requested_end": "2026-10-10T14:00",
            "resource_type": "PROJECTOR",
            "quantity": "1",
        },
    )

    assert response.status_code == 400


# ============================================================
# 7. MULTIPLE UNAVAILABLE RESOURCES
# ============================================================

def test_multiple_unavailable_resources(
    client,
    app,
    event,
):

    with app.app_context():

        resources = []

        for number in range(1, 3):

            resource = create_resource(
                ResourceType.MICROPHONE,
                f"Microphone {number}",
            )

            resources.append(resource)

        db.session.commit()

        existing_request = ResourceRequest(
            event_id=event,
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

        db.session.add(existing_request)

        db.session.flush()

        for resource in resources:

            allocation = Allocation(
                resource_id=resource.id,
                event_id=event,
                request_id=existing_request.id,
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
                status=AllocationStatus.ALLOCATED,
            )

            db.session.add(allocation)

        db.session.commit()

    response = client.post(
        "/requests/create",
        data={
            "event_id": str(event),
            "requested_start": "2026-10-10T10:00",
            "requested_end": "2026-10-10T14:00",
            "resource_type": "MICROPHONE",
            "quantity": "2",
        },
    )

    assert response.status_code == 400


# ============================================================
# 8. DUPLICATE RESOURCE TYPE
# ============================================================

def test_duplicate_resource_type(
    client,
    app,
    event,
):

    with app.app_context():

        create_resource(
            ResourceType.PROJECTOR,
            "Projector 1",
        )

        create_resource(
            ResourceType.PROJECTOR,
            "Projector 2",
        )

        db.session.commit()

    response = client.post(
        "/requests/create",
        data=MultiDict(
            [
                (
                    "event_id",
                    str(event),
                ),
                (
                    "requested_start",
                    "2026-10-10T10:00",
                ),
                (
                    "requested_end",
                    "2026-10-10T14:00",
                ),

                (
                    "resource_type",
                    "PROJECTOR",
                ),
                (
                    "quantity",
                    "1",
                ),

                (
                    "resource_type",
                    "PROJECTOR",
                ),
                (
                    "quantity",
                    "1",
                ),
            ]
        ),
    )

    assert response.status_code == 400


# ============================================================
# 9. REQUEST TIME MUST BE INSIDE EVENT
# ============================================================

def test_request_time_must_be_inside_event(
    client,
    app,
    event,
):

    with app.app_context():

        create_resource(
            ResourceType.HALL,
            "Auditorium",
            capacity=300,
        )

        db.session.commit()

    response = client.post(
        "/requests/create",
        data={
            "event_id": str(event),

            # Event starts at 09:00.
            # Request starts before the event.
            "requested_start": "2026-10-10T08:00",

            "requested_end": "2026-10-10T14:00",

            "resource_type": "HALL",
            "quantity": "1",
        },
    )

    assert response.status_code == 400
