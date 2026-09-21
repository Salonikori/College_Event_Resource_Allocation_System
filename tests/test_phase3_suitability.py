from datetime import datetime

from app import create_app, db
from app.models import (
    Event,
    Resource,
    ResourceType
)
from app.services.suitability import check_suitability


def create_test_event(attendance=100):
    """
    Create a test event.
    """

    event = Event(
        name="Test Event",
        organizer="Test Organizer",
        expected_attendance=attendance,
        start_dt=datetime(2026, 10, 10, 10, 0),
        end_dt=datetime(2026, 10, 10, 14, 0)
    )

    db.session.add(event)
    db.session.commit()

    return event


def setup_database():
    """
    Create a test Flask application.
    """

    app = create_app()

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    return app


def test_suitable_resource():
    """
    Active resource with correct type
    and sufficient capacity should be suitable.
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        event = create_test_event(attendance=100)

        resource = Resource(
            name="Main Hall",
            type=ResourceType.HALL,
            capacity=200,
            is_active=True
        )

        db.session.add(resource)
        db.session.commit()

        reasons = check_suitability(
            resource,
            event,
            ResourceType.HALL
        )

        assert reasons == []


def test_inactive_resource():
    """
    An inactive resource should return
    an INACTIVE reason.
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        event = create_test_event(attendance=100)

        resource = Resource(
            name="Main Hall",
            type=ResourceType.HALL,
            capacity=200,
            is_active=False
        )

        db.session.add(resource)
        db.session.commit()

        reasons = check_suitability(
            resource,
            event,
            ResourceType.HALL
        )

        codes = [code for code, message in reasons]

        assert "INACTIVE" in codes


def test_wrong_resource_type():
    """
    A resource with the wrong type should return
    a TYPE_MISMATCH reason.
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        event = create_test_event(attendance=100)

        resource = Resource(
            name="Computer Lab",
            type=ResourceType.LAB,
            capacity=200,
            is_active=True
        )

        db.session.add(resource)
        db.session.commit()

        reasons = check_suitability(
            resource,
            event,
            ResourceType.HALL
        )

        codes = [code for code, message in reasons]

        assert "TYPE_MISMATCH" in codes


def test_insufficient_capacity():
    """
    A resource with insufficient capacity should return
    an INSUFFICIENT_CAPACITY reason.
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        event = create_test_event(attendance=150)

        resource = Resource(
            name="Small Hall",
            type=ResourceType.HALL,
            capacity=100,
            is_active=True
        )

        db.session.add(resource)
        db.session.commit()

        reasons = check_suitability(
            resource,
            event,
            ResourceType.HALL
        )

        codes = [code for code, message in reasons]

        assert "INSUFFICIENT_CAPACITY" in codes


def test_multiple_suitability_failures():
    """
    A resource can fail multiple suitability checks.
    """

    app = setup_database()

    with app.app_context():
        db.drop_all()
        db.create_all()

        event = create_test_event(attendance=150)

        resource = Resource(
            name="Small Lab",
            type=ResourceType.LAB,
            capacity=100,
            is_active=False
        )

        db.session.add(resource)
        db.session.commit()

        reasons = check_suitability(
            resource,
            event,
            ResourceType.HALL
        )

        codes = [code for code, message in reasons]

        assert "INACTIVE" in codes
        assert "TYPE_MISMATCH" in codes
        assert "INSUFFICIENT_CAPACITY" in codes