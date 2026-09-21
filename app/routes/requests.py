from flask import Blueprint, render_template

from app.models import ResourceRequest


requests_bp = Blueprint(
    "requests",
    __name__,
    url_prefix="/requests",
)


@requests_bp.route("/")
def requests():
    requests = ResourceRequest.query.order_by(
        ResourceRequest.created_at.desc()
    ).all()

    return render_template(
        "requests.html",
        requests=requests,
    )