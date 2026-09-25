import pytest

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Role, User


# ============================================================
# APP FIXTURE
# ============================================================

@pytest.fixture
def app():
    """
    Create a fresh Flask application and database
    for tests that do not define their own app fixture.

    IMPORTANT: the app context is only held open for setup
    and teardown, never across `yield`. Flask reuses an
    already-active app context for test-client requests
    instead of pushing a fresh one, which would make
    Flask-Login's per-request user cache (`g._login_user`)
    leak between different simulated users/clients within
    the same test. Popping the context before `yield` keeps
    every test-client request fully independent, exactly as
    it would be for real, separate HTTP requests.
    """

    app = create_app()

    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    with app.app_context():

        # ----------------------------------------------------
        # Start each test with a clean database
        # ----------------------------------------------------

        db.drop_all()
        db.create_all()

    yield app

    # ----------------------------------------------------
    # Cleanup
    # ----------------------------------------------------

    with app.app_context():

        db.session.remove()
        db.drop_all()


# ============================================================
# DATABASE SESSION FIXTURE
# ============================================================

@pytest.fixture
def session(app):
    """
    Provide a SQLAlchemy session for tests that request
    a `session` fixture.
    """

    with app.app_context():

        yield db.session

        db.session.rollback()
        db.session.remove()


# ============================================================
# USER FIXTURES
# ============================================================
#
# The application now requires an authenticated session for
# every page. These fixtures create a standing Admin and
# Organizer account so route-level tests can log in exactly
# the way a real user would, through the /auth/login route.
# ============================================================

@pytest.fixture
def admin_user(app):

    with app.app_context():

        user = User.query.filter_by(
            email="test-admin@resourcehub.edu"
        ).first()

        if user is None:

            user = User(
                name="Test Admin",
                email="test-admin@resourcehub.edu",
                password_hash=generate_password_hash(
                    "password123"
                ),
                role=Role.ADMIN,
            )

            db.session.add(user)
            db.session.commit()

        return user.id


@pytest.fixture
def organizer_user(app):

    with app.app_context():

        user = User.query.filter_by(
            email="test-organizer@resourcehub.edu"
        ).first()

        if user is None:

            user = User(
                name="Test Organizer",
                email="test-organizer@resourcehub.edu",
                password_hash=generate_password_hash(
                    "password123"
                ),
                role=Role.ORGANIZER,
            )

            db.session.add(user)
            db.session.commit()

        return user.id


# ============================================================
# CLIENT FIXTURE
# ============================================================
#
# The existing test suite predates authentication and drives
# every route as a super-user, so the shared `client` fixture
# logs in as an Admin by default: this keeps every existing
# route-level assertion valid without rewriting each test.
# Tests that specifically need organizer-scoped behaviour can
# use the `organizer_client` fixture instead.
# ============================================================

@pytest.fixture
def client(app, admin_user):

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
def organizer_client(app, organizer_user):

    test_client = app.test_client()

    test_client.post(
        "/auth/login",
        data={
            "email": "test-organizer@resourcehub.edu",
            "password": "password123",
        },
    )

    return test_client
