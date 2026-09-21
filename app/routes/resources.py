from flask import Blueprint, render_template

from app.models import Resource


resources_bp = Blueprint(
    "resources",
    __name__,
    url_prefix="/resources",
)


@resources_bp.route("/")
def resources():
    resources = Resource.query.order_by(
        Resource.name.asc()
    ).all()

    return render_template(
        "resources.html",
        resources=resources,
    )