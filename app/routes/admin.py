from flask import Blueprint, render_template

from app.models import ResourceRequest, RequestStatus


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/approvals",
)


@admin_bp.route("/")
def approvals():
    requests = ResourceRequest.query.filter(
        ResourceRequest.status == RequestStatus.PENDING
    ).order_by(
        ResourceRequest.created_at.asc()
    ).all()

    return render_template(
        "approvals.html",
        requests=requests,
    )