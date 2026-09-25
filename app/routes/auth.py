from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from urllib.parse import urlparse

from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from app import db

from app.models import Role, User


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
)


# ============================================================
# LOGIN
# ============================================================

@auth_bp.route(
    "/login",
    methods=["GET", "POST"],
)
def login():

    if current_user.is_authenticated:
        return redirect(
            url_for("dashboard.dashboard")
        )

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get(
            "password", ""
        )

        if not email or not password:

            flash(
                "Email and password are required.",
                "error",
            )

            return render_template(
                "auth/login.html",
                form_data=request.form,
            )

        user = (
            User.query
            .filter_by(email=email)
            .first()
        )

        if (
            user is None
            or not check_password_hash(
                user.password_hash, password
            )
        ):

            flash(
                "Invalid email or password.",
                "error",
            )

            return render_template(
                "auth/login.html",
                form_data=request.form,
            )

        if not user.is_active_account:

            flash(
                "This account has been deactivated. "
                "Contact an administrator.",
                "error",
            )

            return render_template(
                "auth/login.html",
                form_data=request.form,
            )

        login_user(user)

        flash(
            f"Welcome back, {user.name}.",
            "success",
        )

        next_page = request.args.get("next", "").strip()
        # Never redirect to an arbitrary external URL supplied through
        # the query string. Only local absolute paths are accepted.
        parsed_next = urlparse(next_page)
        if (
            not next_page
            or parsed_next.scheme
            or parsed_next.netloc
            or not next_page.startswith("/")
            or next_page.startswith("//")
        ):
            next_page = url_for("dashboard.dashboard")

        return redirect(next_page)

    return render_template(
        "auth/login.html",
        form_data={},
    )


# ============================================================
# REGISTER
#
# Self-service registration only creates ORGANIZER accounts.
# Admin accounts are provisioned by an existing admin
# (seeded, or created from the Manage Users screen) so that
# nobody can grant themselves admin rights through the
# public sign-up form.
# ============================================================

@auth_bp.route(
    "/register",
    methods=["GET", "POST"],
)
def register():

    if current_user.is_authenticated:
        return redirect(
            url_for("dashboard.dashboard")
        )

    if request.method == "POST":

        name = request.form.get(
            "name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get(
            "password", ""
        )

        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "error",
            )

            return render_template(
                "auth/register.html",
                form_data=request.form,
            )

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "error",
            )

            return render_template(
                "auth/register.html",
                form_data=request.form,
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error",
            )

            return render_template(
                "auth/register.html",
                form_data=request.form,
            )

        existing = (
            User.query
            .filter_by(email=email)
            .first()
        )

        if existing is not None:

            flash(
                "An account with this email already exists.",
                "error",
            )

            return render_template(
                "auth/register.html",
                form_data=request.form,
            )

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(
                password
            ),
            role=Role.ORGANIZER,
        )

        db.session.add(user)
        db.session.commit()

        flash(
            "Account created. You can now log in.",
            "success",
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "auth/register.html",
        form_data={},
    )


# ============================================================
# LOGOUT
# ============================================================

@auth_bp.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "info",
    )

    return redirect(
        url_for("auth.login")
    )
