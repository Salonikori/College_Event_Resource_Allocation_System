from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import os


db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    # ------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "dev-secret-key"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///resource_allocation.db"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ------------------------------------------------------------
    # Initialize database
    # ------------------------------------------------------------

    db.init_app(app)

    # Import models so SQLAlchemy knows about all tables
    from app import models

    # ------------------------------------------------------------
    # Create database tables
    # ------------------------------------------------------------

    with app.app_context():
        db.create_all()

 
    # ------------------------------------------------------------
    # Register routes
    # ------------------------------------------------------------

    from app.routes.dashboard import dashboard_bp
    from app.routes.events import events_bp
    from app.routes.resources import resources_bp
    from app.routes.requests import requests_bp
    from app.routes.availability import availability_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(availability_bp)
    app.register_blueprint(admin_bp)
    # ------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template(
            "error.html",
            error_code=404,
            message="The page you are looking for does not exist."
        ), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.exception(error)

        return render_template(
            "error.html",
            error_code=500,
            message="Something went wrong on the server."
        ), 500

    return app