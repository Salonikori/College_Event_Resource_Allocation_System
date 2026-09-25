"""
Seed script for ResourceHub.

Creates:
- One Admin account
- One Organizer (demo) account
- A handful of sample resources so the app is usable
  immediately after setup.

Usage:
    python seed.py
"""

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Resource, ResourceType, Role, User


def seed():

    app = create_app()

    with app.app_context():

        # ----------------------------------------------------
        # Users
        # ----------------------------------------------------

        if User.query.filter_by(
            email="admin@resourcehub.edu"
        ).first() is None:

            admin = User(
                name="System Admin",
                email="admin@resourcehub.edu",
                password_hash=generate_password_hash(
                    "admin123"
                ),
                role=Role.ADMIN,
            )

            db.session.add(admin)
            print("Created admin: admin@resourcehub.edu / admin123")

        else:
            print("Admin already exists, skipping.")

        if User.query.filter_by(
            email="organizer@resourcehub.edu"
        ).first() is None:

            organizer = User(
                name="Demo Organizer",
                email="organizer@resourcehub.edu",
                password_hash=generate_password_hash(
                    "organizer123"
                ),
                role=Role.ORGANIZER,
            )

            db.session.add(organizer)
            print(
                "Created organizer: "
                "organizer@resourcehub.edu / organizer123"
            )

        else:
            print("Demo organizer already exists, skipping.")

        db.session.commit()

        # ----------------------------------------------------
        # Resources
        # ----------------------------------------------------

        sample_resources = [
            ("Main Auditorium", ResourceType.HALL, 300),
            ("Seminar Hall B", ResourceType.HALL, 120),
            ("Computer Lab 1", ResourceType.LAB, 60),
            ("Physics Lab", ResourceType.LAB, 40),
            ("Projector - Portable A", ResourceType.PROJECTOR, None),
            ("Projector - Portable B", ResourceType.PROJECTOR, None),
            ("Wireless Microphone 1", ResourceType.MICROPHONE, None),
            ("Wireless Microphone 2", ResourceType.MICROPHONE, None),
            ("PA Speaker Set", ResourceType.SPEAKER, None),
            ("Laptop Cart (20 units)", ResourceType.COMPUTER, 20),
        ]

        created_count = 0

        for name, rtype, capacity in sample_resources:

            if Resource.query.filter_by(name=name).first():
                continue

            resource = Resource(
                name=name,
                type=rtype,
                capacity=capacity,
                is_active=True,
            )

            db.session.add(resource)
            created_count += 1

        db.session.commit()

        print(f"Created {created_count} sample resource(s).")
        print("Seeding complete.")


if __name__ == "__main__":
    seed()
