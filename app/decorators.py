from functools import wraps

from flask import abort

from flask_login import current_user


# ============================================================
# ADMIN REQUIRED
# ============================================================
#
# Use this on top of routes that only an Admin may access
# (resource management, approvals/rejections, cancelling
# other people's allocations).
#
# Assumes the route is already behind login (Flask-Login's
# login_manager.login_view handles the "not logged in" case
# for every protected blueprint), so this only needs to
# check the role of the already-authenticated user.
# ============================================================

def admin_required(view_func):

    @wraps(view_func)
    def wrapped(*args, **kwargs):

        if not current_user.is_authenticated:
            abort(401)

        if not current_user.is_admin():
            abort(403)

        return view_func(*args, **kwargs)

    return wrapped
