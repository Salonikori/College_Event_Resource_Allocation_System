from app.models import Role, User
from tests.auth_helpers import login_as_admin, login_as_organizer


# ============================================================
# LOGIN REQUIRED
# ============================================================

def test_anonymous_user_is_redirected_to_login(app):

    client = app.test_client()

    response = client.get("/events/")

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_login_with_valid_credentials_succeeds(app):

    from werkzeug.security import generate_password_hash
    from app import db

    with app.app_context():

        db.session.add(
            User(
                name="Jane Organizer",
                email="jane@resourcehub.edu",
                password_hash=generate_password_hash("secret123"),
                role=Role.ORGANIZER,
            )
        )
        db.session.commit()

    client = app.test_client()

    response = client.post(
        "/auth/login",
        data={
            "email": "jane@resourcehub.edu",
            "password": "secret123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Log out" in response.data


def test_login_with_invalid_password_fails(app):

    from werkzeug.security import generate_password_hash
    from app import db

    with app.app_context():

        db.session.add(
            User(
                name="Jane Organizer",
                email="jane2@resourcehub.edu",
                password_hash=generate_password_hash("secret123"),
                role=Role.ORGANIZER,
            )
        )
        db.session.commit()

    client = app.test_client()

    response = client.post(
        "/auth/login",
        data={
            "email": "jane2@resourcehub.edu",
            "password": "wrong-password",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


# ============================================================
# ROLE-BASED ACCESS: RESOURCE MANAGEMENT (ADMIN ONLY)
# ============================================================

def test_organizer_cannot_create_resource(app):

    client = login_as_organizer(app)

    response = client.get("/resources/create")

    assert response.status_code == 403


def test_admin_can_create_resource(app):

    client = login_as_admin(app)

    response = client.get("/resources/create")

    assert response.status_code == 200


def test_organizer_cannot_deactivate_resource(app):

    from app import db
    from app.models import Resource, ResourceType

    with app.app_context():

        resource = Resource(
            name="Test Hall",
            type=ResourceType.HALL,
            capacity=100,
            is_active=True,
        )

        db.session.add(resource)
        db.session.commit()

        resource_id = resource.id

    client = login_as_organizer(app)

    response = client.post(
        f"/resources/{resource_id}/deactivate"
    )

    assert response.status_code == 403

    with app.app_context():

        resource = db.session.get(Resource, resource_id)

        assert resource.is_active is True


# ============================================================
# ROLE-BASED ACCESS: APPROVALS (ADMIN ONLY)
# ============================================================

def test_organizer_cannot_view_approvals(app):

    client = login_as_organizer(app)

    response = client.get("/approvals/")

    assert response.status_code == 403


def test_admin_can_view_approvals(app):

    client = login_as_admin(app)

    response = client.get("/approvals/")

    assert response.status_code == 200


# ============================================================
# OWNERSHIP: EVENTS
# ============================================================

def test_organizer_only_sees_own_events(app):

    from app import db
    from app.models import Event, EventStatus, User as UserModel

    with app.app_context():

        alice = UserModel.query.filter_by(
            email="alice@resourcehub.edu"
        ).first()

        if alice is None:

            from werkzeug.security import generate_password_hash

            alice = UserModel(
                name="Alice",
                email="alice@resourcehub.edu",
                password_hash=generate_password_hash("password123"),
                role=Role.ORGANIZER,
            )

            db.session.add(alice)
            db.session.commit()

        alice_id = alice.id

        from datetime import datetime, timedelta

        now = datetime.utcnow() + timedelta(days=1)

        db.session.add(
            Event(
                name="Alice's Event",
                organizer="Alice",
                organizer_id=alice_id,
                expected_attendance=50,
                start_dt=now,
                end_dt=now + timedelta(hours=2),
                status=EventStatus.DRAFT,
            )
        )

        db.session.commit()

    # A different organizer (from login_as_organizer) should not
    # see Alice's event in their own event list.
    client = login_as_organizer(app)

    response = client.get("/events/")

    assert response.status_code == 200
    assert b"Alice&#39;s Event" not in response.data
    assert b"Alice's Event" not in response.data


def test_organizer_cannot_edit_others_event(app):

    from app import db
    from app.models import Event, EventStatus, User as UserModel
    from werkzeug.security import generate_password_hash
    from datetime import datetime, timedelta

    with app.app_context():

        bob = UserModel(
            name="Bob",
            email="bob@resourcehub.edu",
            password_hash=generate_password_hash("password123"),
            role=Role.ORGANIZER,
        )

        db.session.add(bob)
        db.session.commit()

        now = datetime.utcnow() + timedelta(days=1)

        event = Event(
            name="Bob's Event",
            organizer="Bob",
            organizer_id=bob.id,
            expected_attendance=50,
            start_dt=now,
            end_dt=now + timedelta(hours=2),
            status=EventStatus.DRAFT,
        )

        db.session.add(event)
        db.session.commit()

        event_id = event.id

    # A different organizer must not be able to edit Bob's event.
    client = login_as_organizer(app)

    response = client.get(f"/events/{event_id}/edit")

    assert response.status_code == 403

    # But an admin must be able to.
    admin_client = login_as_admin(app)

    response = admin_client.get(f"/events/{event_id}/edit")

    assert response.status_code == 200
