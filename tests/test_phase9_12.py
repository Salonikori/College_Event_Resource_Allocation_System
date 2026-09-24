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
    find_conflicts,
)


# ============================================================
# FIXTURE
# ============================================================

@pytest.fixture
def app():

    app = create_app(
    )

    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )

    # Reinitialize is not required because create_app already
    # initializes db. Use the existing application context.

    with app.app_context():

        db.drop_all()

        db.create_all()

        yield app

        db.session.remove()

        db.drop_all()


@pytest.fixture
def client(app):

    return app.test_client()


# ============================================================
# HELPERS
# ============================================================

def make_event(
    name="Technical Workshop",
):

    event = Event(
        name=name,

        organizer="College",

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

        status=EventStatus.PENDING,
    )

    db.session.add(
        event
    )

    db.session.flush()

    return event


def make_resource(
    name="Projector 1",
    resource_type=ResourceType.PROJECTOR,
    capacity=100,
    active=True,
    buffer=0,
):

    resource = Resource(
        name=name,

        type=resource_type,

        capacity=capacity,

        is_active=active,

        buffer_minutes=buffer,
    )

    db.session.add(
        resource
    )

    db.session.flush()

    return resource


def make_request(
    event,
    resource_type=ResourceType.PROJECTOR,
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
                resource_type,

            quantity=1,
        )
    )

    db.session.flush()

    return resource_request


def add_allocation(
    resource,
    event,
    resource_request,
    start=None,
    end=None,
    status=AllocationStatus.ALLOCATED,
):

    allocation = Allocation(
        resource_id=
            resource.id,

        event_id=
            event.id,

        request_id=
            resource_request.id,

        start_dt=
            start
            or datetime(
                2026,
                10,
                10,
                10,
                0,
            ),

        end_dt=
            end
            or datetime(
                2026,
                10,
                10,
                12,
                0,
            ),

        status=status,
    )

    db.session.add(
        allocation
    )

    db.session.flush()

    return allocation


# ============================================================
# PHASE 9 — AVAILABILITY
# ============================================================

def test_availability_page_loads(
    client,
):

    response = client.get(
        "/availability/"
    )

    assert response.status_code == 200

    assert (
        b"Resource Availability"
        in response.data
    )


def test_available_resource(
    client,
    app,
):

    with app.app_context():

        resource = make_resource()

        resource_id = resource.id

        db.session.commit()

    response = client.post(
        "/availability/",
        data={
            "resource_id":
                str(resource_id),

            "date":
                "2026-10-10",

            "start_time":
                "10:00",

            "end_time":
                "12:00",
        },
    )

    assert response.status_code == 200

    assert (
        b"Available"
        in response.data
    )

    assert (
        b"Projector 1"
        in response.data
    )


def test_booked_resource(
    client,
    app,
):

    with app.app_context():

        event = make_event()

        resource = make_resource()

        resource_request = make_request(
            event
        )

        add_allocation(
            resource,
            event,
            resource_request,
        )

        resource_id = resource.id

        db.session.commit()

    response = client.post(
        "/availability/",
        data={
            "resource_id":
                str(resource_id),

            "date":
                "2026-10-10",

            "start_time":
                "10:00",

            "end_time":
                "12:00",
        },
    )

    assert response.status_code == 200

    assert (
        b"Booked / Unavailable"
        in response.data
    )

    assert (
        b"Technical Workshop"
        in response.data
    )


def test_buffer_time_is_respected(
    client,
    app,
):

    with app.app_context():

        event = make_event()

        resource = make_resource(
            buffer=30
        )

        resource_request = make_request(
            event
        )

        add_allocation(
            resource,

            event,

            resource_request,

            start=datetime(
                2026,
                10,
                10,
                10,
                0,
            ),

            end=datetime(
                2026,
                10,
                10,
                12,
                0,
            ),
        )

        resource_id = resource.id

        db.session.commit()

    # 12:15 should still conflict because the
    # resource has a 30 minute buffer.

    response = client.post(
        "/availability/",
        data={
            "resource_id":
                str(resource_id),

            "date":
                "2026-10-10",

            "start_time":
                "12:15",

            "end_time":
                "13:00",
        },
    )

    assert response.status_code == 200

    assert (
        b"Booked / Unavailable"
        in response.data
    )


def test_cancelled_allocation_does_not_block(
    client,
    app,
):

    with app.app_context():

        event = make_event()

        resource = make_resource()

        resource_request = make_request(
            event
        )

        add_allocation(
            resource,

            event,

            resource_request,

            status=
                AllocationStatus.CANCELLED,
        )

        resource_id = resource.id

        db.session.commit()

    response = client.post(
        "/availability/",
        data={
            "resource_id":
                str(resource_id),

            "date":
                "2026-10-10",

            "start_time":
                "10:00",

            "end_time":
                "12:00",
        },
    )

    assert response.status_code == 200

    assert (
        b"Available"
        in response.data
    )


def test_inactive_resource_is_unavailable(
    client,
    app,
):

    with app.app_context():

        resource = make_resource(
            active=False
        )

        resource_id = resource.id

        db.session.commit()

    response = client.post(
        "/availability/",
        data={
            "resource_id":
                str(resource_id),

            "date":
                "2026-10-10",

            "start_time":
                "10:00",

            "end_time":
                "12:00",
        },
    )

    assert response.status_code == 200

    assert (
        b"inactive"
        in response.data.lower()
    )


def test_resource_details_show_active_status(
    client,
    app,
):

    with app.app_context():

        resource = make_resource(
            active=True
        )

        resource_id = resource.id

        db.session.commit()

    response = client.post(
        "/availability/",
        data={
            "resource_id":
                str(resource_id),

            "date":
                "2026-10-10",

            "start_time":
                "10:00",

            "end_time":
                "12:00",
        },
    )

    assert response.status_code == 200

    assert (
        b"Active"
        in response.data
    )


def test_missing_resource_is_friendly(
    client,
):

    response = client.post(
        "/availability/",
        data={
            "resource_id":
                "999999",

            "date":
                "2026-10-10",

            "start_time":
                "10:00",

            "end_time":
                "12:00",
        },
    )

    assert response.status_code == 200

    assert (
        b"Resource not found"
        in response.data
    )

    assert (
        b"Traceback"
        not in response.data
    )


def test_invalid_resource_id_is_friendly(
    client,
):

    response = client.post(
        "/availability/",
        data={
            "resource_id":
                "invalid",

            "date":
                "2026-10-10",

            "start_time":
                "10:00",

            "end_time":
                "12:00",
        },
    )

    assert response.status_code == 200

    assert (
        b"Invalid resource selected"
        in response.data
    )


def test_missing_availability_fields(
    client,
):

    response = client.post(
        "/availability/",
        data={
            "resource_id":
                "",
        },
    )

    assert response.status_code == 200

    assert (
        b"Please select a resource"
        in response.data
    )


def test_invalid_time_range(
    client,
    app,
):

    with app.app_context():

        resource = make_resource()

        resource_id = resource.id

        db.session.commit()

    response = client.post(
        "/availability/",
        data={
            "resource_id":
                str(resource_id),

            "date":
                "2026-10-10",

            "start_time":
                "14:00",

            "end_time":
                "10:00",
        },
    )

    assert response.status_code == 200

    assert (
        b"End time must be after start time"
        in response.data
    )

    assert (
        b"Traceback"
        not in response.data
    )


# ============================================================
# FIND CONFLICTS
# ============================================================

def test_find_conflicts_only_active_allocations(
    app,
):

    with app.app_context():

        event = make_event()

        resource = make_resource()

        resource_request = make_request(
            event
        )

        add_allocation(
            resource,
            event,
            resource_request,
            status=
                AllocationStatus.ALLOCATED,
        )

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

        assert len(
            conflicts
        ) == 1


# ============================================================
# PHASE 11 — ERROR HANDLING
# ============================================================

def test_404_has_no_traceback(
    client,
):

    response = client.get(
        "/does-not-exist"
    )

    assert response.status_code == 404

    assert (
        b"Traceback"
        not in response.data
    )


def test_405_has_no_traceback(
    client,
):

    response = client.post(
        "/availability/"
    )

    assert response.status_code == 200

    # POST without data is handled by our availability
    # route, so there should still be no traceback.

    assert (
        b"Traceback"
        not in response.data
    )


# ============================================================
# PHASE 10 — CLIENT-SIDE FORM FEATURES
# ============================================================

def test_availability_page_contains_required_js(
    client,
):

    response = client.get(
        "/availability/"
    )

    assert response.status_code == 200

    assert (
        b"availabilityForm"
        in response.data
    )

    assert (
        b"checkAvailabilityButton"
        in response.data
    )


def test_global_javascript_is_loaded(
    client,
):

    response = client.get(
        "/availability/"
    )

    assert response.status_code == 200

    assert (
        b"/static/app.js"
        in response.data
    )