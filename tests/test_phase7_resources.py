from app import create_app, db
from app.models import (
    Resource,
    ResourceType,
)


def setup_app():

    app = create_app()

    app.config["TESTING"] = True

    with app.app_context():

        db.drop_all()
        db.create_all()

    return app


# ============================================================
# CREATE RESOURCE
# ============================================================

def test_create_resource():

    app = setup_app()

    client = app.test_client()

    response = client.post(
        "/resources/create",
        data={
            "name": "Main Auditorium",
            "type": "HALL",
            "capacity": "300",
            "buffer_minutes": "30",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        resource = Resource.query.filter_by(
            name="Main Auditorium"
        ).first()

        assert resource is not None
        assert resource.type == ResourceType.HALL
        assert resource.capacity == 300
        assert resource.buffer_minutes == 30
        assert resource.is_active is True


# ============================================================
# EDIT RESOURCE
# ============================================================

def test_edit_resource():

    app = setup_app()

    with app.app_context():

        resource = Resource(
            name="Hall A",
            type=ResourceType.HALL,
            capacity=100,
            is_active=True,
            buffer_minutes=15,
        )

        db.session.add(resource)
        db.session.commit()

        resource_id = resource.id

    client = app.test_client()

    response = client.post(
        f"/resources/{resource_id}/edit",
        data={
            "name": "Hall A Updated",
            "type": "HALL",
            "capacity": "200",
            "buffer_minutes": "30",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        resource = db.session.get(
            Resource,
            resource_id
        )

        assert resource.name == "Hall A Updated"
        assert resource.capacity == 200
        assert resource.buffer_minutes == 30
        assert resource.type == ResourceType.HALL
        assert resource.is_active is True


# ============================================================
# EDIT RESOURCE TYPE
# ============================================================

def test_edit_resource_type():

    app = setup_app()

    with app.app_context():

        resource = Resource(
            name="Equipment 1",
            type=ResourceType.PROJECTOR,
            capacity=None,
            is_active=True,
            buffer_minutes=0,
        )

        db.session.add(resource)
        db.session.commit()

        resource_id = resource.id

    client = app.test_client()

    response = client.post(
        f"/resources/{resource_id}/edit",
        data={
            "name": "Equipment 1",
            "type": "COMPUTER",
            "capacity": "1",
            "buffer_minutes": "5",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        resource = db.session.get(
            Resource,
            resource_id
        )

        assert resource.type == ResourceType.COMPUTER
        assert resource.capacity == 1


# ============================================================
# DEACTIVATE RESOURCE
# ============================================================

def test_deactivate_resource():

    app = setup_app()

    with app.app_context():

        resource = Resource(
            name="Projector 1",
            type=ResourceType.PROJECTOR,
            capacity=None,
            is_active=True,
            buffer_minutes=0,
        )

        db.session.add(resource)
        db.session.commit()

        resource_id = resource.id

    client = app.test_client()

    response = client.post(
        f"/resources/{resource_id}/deactivate",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        resource = db.session.get(
            Resource,
            resource_id
        )

        assert resource.is_active is False


# ============================================================
# ACTIVATE RESOURCE
# ============================================================

def test_activate_resource():

    app = setup_app()

    with app.app_context():

        resource = Resource(
            name="Projector 2",
            type=ResourceType.PROJECTOR,
            capacity=None,
            is_active=False,
            buffer_minutes=0,
        )

        db.session.add(resource)
        db.session.commit()

        resource_id = resource.id

    client = app.test_client()

    response = client.post(
        f"/resources/{resource_id}/activate",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        resource = db.session.get(
            Resource,
            resource_id
        )

        assert resource.is_active is True


# ============================================================
# INVALID RESOURCE TYPE
# ============================================================

def test_invalid_resource_type():

    app = setup_app()

    client = app.test_client()

    response = client.post(
        "/resources/create",
        data={
            "name": "Invalid Resource",
            "type": "INVALID_TYPE",
            "capacity": "100",
            "buffer_minutes": "0",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        resource = Resource.query.filter_by(
            name="Invalid Resource"
        ).first()

        assert resource is None


# ============================================================
# NEGATIVE CAPACITY
# ============================================================

def test_negative_capacity():

    app = setup_app()

    client = app.test_client()

    response = client.post(
        "/resources/create",
        data={
            "name": "Invalid Hall",
            "type": "HALL",
            "capacity": "-100",
            "buffer_minutes": "0",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        resource = Resource.query.filter_by(
            name="Invalid Hall"
        ).first()

        assert resource is None


# ============================================================
# NEGATIVE BUFFER
# ============================================================

def test_negative_buffer():

    app = setup_app()

    client = app.test_client()

    response = client.post(
        "/resources/create",
        data={
            "name": "Invalid Projector",
            "type": "PROJECTOR",
            "capacity": "",
            "buffer_minutes": "-10",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        resource = Resource.query.filter_by(
            name="Invalid Projector"
        ).first()

        assert resource is None


# ============================================================
# EDIT NON-EXISTENT RESOURCE
# ============================================================

def test_edit_nonexistent_resource():

    app = setup_app()

    client = app.test_client()

    response = client.post(
        "/resources/99999/edit",
        data={
            "name": "Does Not Exist",
            "type": "HALL",
            "capacity": "100",
            "buffer_minutes": "0",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200


# ============================================================
# ACTIVATE NON-EXISTENT RESOURCE
# ============================================================

def test_activate_nonexistent_resource():

    app = setup_app()

    client = app.test_client()

    response = client.post(
        "/resources/99999/activate",
        follow_redirects=True,
    )

    assert response.status_code == 200


# ============================================================
# DEACTIVATE NON-EXISTENT RESOURCE
# ============================================================

def test_deactivate_nonexistent_resource():

    app = setup_app()

    client = app.test_client()

    response = client.post(
        "/resources/99999/deactivate",
        follow_redirects=True,
    )

    assert response.status_code == 200