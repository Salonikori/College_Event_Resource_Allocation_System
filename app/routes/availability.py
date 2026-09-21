from flask import Blueprint, render_template

from app.models import Allocation, Resource


availability_bp = Blueprint(
    "availability",
    __name__,
    url_prefix="/availability",
)


@availability_bp.route("/")
def availability():
    resources = Resource.query.order_by(
        Resource.name.asc()
    ).all()

    allocations = Allocation.query.order_by(
        Allocation.start_dt.asc()
    ).all()

    return render_template(
        "availability.html",
        resources=resources,
        allocations=allocations,
    )