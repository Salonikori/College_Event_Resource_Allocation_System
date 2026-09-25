import os

from flask import Flask, redirect, render_template, url_for

from flask_sqlalchemy import SQLAlchemy

from flask_login import LoginManager


db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"


def create_app(test_config=None):

    app = Flask(__name__)


    # ========================================================
    # DEFAULT CONFIG
    # ========================================================

    app.config.from_mapping(

        SECRET_KEY=os.getenv(
            "SECRET_KEY",
            "dev-secret-key",
        ),

        SQLALCHEMY_DATABASE_URI=os.getenv(
            "DATABASE_URL",
            "sqlite:///resource_allocation.db",
        ),

        SQLALCHEMY_TRACK_MODIFICATIONS=False,

    )


    # ========================================================
    # TEST CONFIG
    # ========================================================

    if test_config:

        app.config.update(
            test_config
        )


    # ========================================================
    # DATABASE
    # ========================================================

    db.init_app(
        app
    )

    login_manager.init_app(
        app
    )


    # Import models.

    from app import models


    @login_manager.user_loader
    def load_user(user_id):
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return None
        return db.session.get(models.User, user_id)


    # ========================================================
    # CREATE TABLES
    # ========================================================

    with app.app_context():

        db.create_all()


    # ========================================================
    # BLUEPRINTS
    # ========================================================

    from app.routes.dashboard import (
        dashboard_bp
    )

    from app.routes.events import (
        events_bp
    )

    from app.routes.resources import (
        resources_bp
    )

    from app.routes.requests import (
        requests_bp
    )

    from app.routes.availability import (
        availability_bp
    )

    from app.routes.admin import (
        admin_bp
    )

    from app.routes.auth import (
        auth_bp
    )


    app.register_blueprint(
        auth_bp
    )

    app.register_blueprint(
        dashboard_bp
    )

    app.register_blueprint(
        events_bp
    )

    app.register_blueprint(
        resources_bp
    )

    app.register_blueprint(
        requests_bp
    )

    app.register_blueprint(
        availability_bp
    )

    app.register_blueprint(
        admin_bp
    )


    # ========================================================
    # GLOBAL LOGIN ENFORCEMENT
    #
    # Every page in the app requires a logged-in user except
    # the auth blueprint itself (login/register/logout) and
    # static assets. This is simpler and harder to accidentally
    # bypass than adding @login_required to every single route.
    # ========================================================

    from flask_login import current_user

    @app.before_request
    def require_login():

        from flask import request as flask_request

        endpoint = flask_request.endpoint or ""

        exempt = (
            endpoint.startswith("auth.")
            or endpoint == "static"
        )

        if exempt:
            return None

        if not current_user.is_authenticated:

            return redirect(
                url_for(
                    "auth.login",
                    next=flask_request.path,
                )
            )

        return None


    # ========================================================
    # ERROR HANDLERS
    # ========================================================

    @app.errorhandler(400)
    def bad_request(error):

        db.session.rollback()

        return render_template(
            "error.html",

            error_code=400,

            title="Bad Request",

            message=(
                "The request could not be processed. "
                "Please check the entered values and try again."
            ),

        ), 400


    @app.errorhandler(401)
    def unauthorized(error):

        db.session.rollback()

        return redirect(
            url_for("auth.login")
        )


    @app.errorhandler(403)
    def forbidden(error):

        db.session.rollback()

        return render_template(
            "error.html",

            error_code=403,

            title="Access Denied",

            message=(
                "You do not have permission to "
                "perform this action. This area is "
                "restricted to administrators."
            ),

        ), 403


    @app.errorhandler(404)
    def page_not_found(error):

        db.session.rollback()

        return render_template(
            "error.html",

            error_code=404,

            title="Page Not Found",

            message=(
                "The page or resource you are looking "
                "for does not exist."
            ),

        ), 404


    @app.errorhandler(405)
    def method_not_allowed(error):

        db.session.rollback()

        return render_template(
            "error.html",

            error_code=405,

            title="Method Not Allowed",

            message=(
                "This action is not supported "
                "for this page."
            ),

        ), 405


    @app.errorhandler(500)
    def internal_server_error(error):

        db.session.rollback()

        app.logger.exception(
            "Unhandled application error"
        )

        return render_template(
            "error.html",

            error_code=500,

            title="Server Error",

            message=(
                "Something went wrong on the server. "
                "Please try again."
            ),

        ), 500


    return app