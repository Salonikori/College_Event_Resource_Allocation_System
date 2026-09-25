"""
Shared helper for tests that build their own Flask app/client
manually (outside the conftest.py fixtures) and need an
authenticated session to exercise protected routes.
"""

from werkzeug.security import generate_password_hash

from app import db
from app.models import Role, User


def login_as_admin(app):
    """
    Create (if needed) a standing admin user inside the given
    app's database and return a Flask test client that is
    already logged in as that admin.
    """

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

    client = app.test_client()

    client.post(
        "/auth/login",
        data={
            "email": "test-admin@resourcehub.edu",
            "password": "password123",
        },
    )

    return client


def login_as_organizer(app):
    """
    Same as login_as_admin, but for a plain Organizer account.
    """

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

    client = app.test_client()

    client.post(
        "/auth/login",
        data={
            "email": "test-organizer@resourcehub.edu",
            "password": "password123",
        },
    )

    return client
