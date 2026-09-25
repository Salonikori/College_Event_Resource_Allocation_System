from app.models import utcnow_naive

from app import db
from app.models import WaitlistEntry, WaitlistStatus, RequestStatus
from app.services.booking import AllocationError, allocate_request


def add_to_waitlist(request_obj, resource_type, resource_id=None):
    """Create one waiting entry for a request/type combination."""
    existing = (
        WaitlistEntry.query
        .filter_by(
            request_id=request_obj.id,
            resource_type=resource_type,
            status=WaitlistStatus.WAITING,
        )
        .first()
    )
    if existing:
        return existing

    entry = WaitlistEntry(
        request_id=request_obj.id,
        resource_id=resource_id,
        resource_type=resource_type,
        status=WaitlistStatus.WAITING,
    )
    db.session.add(entry)
    return entry


def _cancel_waitlist_entries(request_obj):
    """Close all waiting entries belonging to a request."""
    for entry in request_obj.waitlist_entries:
        if entry.status == WaitlistStatus.WAITING:
            entry.status = WaitlistStatus.CANCELLED


def promote_waitlisted_requests(resource_id=None, resource_type=None):
    """Try waiting requests after a resource is released.

    A promotion is atomic for the whole request. If a request contains
    several resource types, either all of its resources are allocated and
    the request is approved, or the request remains waiting. Once promoted,
    every waiting entry for that request is closed so the same request can
    never be allocated twice by a later promotion pass.
    """
    query = WaitlistEntry.query.filter(
        WaitlistEntry.status == WaitlistStatus.WAITING
    )
    if resource_id is not None:
        query = query.filter(
            (WaitlistEntry.resource_id == resource_id)
            | (WaitlistEntry.resource_id.is_(None))
        )
    if resource_type is not None:
        query = query.filter(WaitlistEntry.resource_type == resource_type)

    entries = query.order_by(WaitlistEntry.created_at.asc()).all()
    promoted = []
    processed_request_ids = set()

    for entry in entries:
        req = entry.request
        if req is None:
            entry.status = WaitlistStatus.CANCELLED
            continue

        if req.id in processed_request_ids:
            continue

        if req.status != RequestStatus.PENDING or req.event is None:
            _cancel_waitlist_entries(req)
            processed_request_ids.add(req.id)
            continue

        try:
            # allocate_request(commit=False) participates in the same
            # transaction as the status change below.
            allocate_request(db.session, req, commit=False)
            req.status = RequestStatus.APPROVED

            for req_entry in req.waitlist_entries:
                if req_entry.status == WaitlistStatus.WAITING:
                    req_entry.status = WaitlistStatus.PROMOTED
                    req_entry.promoted_at = utcnow_naive()

            db.session.commit()
            promoted.append(req.id)
            processed_request_ids.add(req.id)
        except AllocationError:
            db.session.rollback()
            processed_request_ids.add(req.id)
        except Exception:
            db.session.rollback()
            processed_request_ids.add(req.id)

    return promoted
