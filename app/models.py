from datetime import datetime, timezone


def utcnow_naive():
    """Return current UTC time as a naive datetime for existing DB columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
from enum import Enum

from app import db


# ============================================================
# ENUMS
# ============================================================

class ResourceType(Enum):
    HALL = "HALL"
    CLASSROOM = "CLASSROOM"
    LAB = "LAB"
    PROJECTOR = "PROJECTOR"
    MICROPHONE = "MICROPHONE"
    SPEAKER = "SPEAKER"
    COMPUTER = "COMPUTER"
    OTHER = "OTHER"


class EventStatus(Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class RequestStatus(Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class AllocationStatus(Enum):
    ALLOCATED = "ALLOCATED"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"


class Role(Enum):
    ADMIN = "ADMIN"
    ORGANIZER = "ORGANIZER"


# ============================================================
# USER
# ============================================================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(150),
        nullable=False,
    )

    email = db.Column(
        db.String(150),
        nullable=False,
        unique=True,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    role = db.Column(
        db.Enum(Role),
        nullable=False,
        default=Role.ORGANIZER,
    )

    is_active_account = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow_naive,
    )

    events = db.relationship(
        "Event",
        back_populates="organizer_user",
    )

    # ---- Flask-Login required interface ----

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.is_active_account

    def is_admin(self):
        return self.role == Role.ADMIN

    def __repr__(self):
        return f"<User {self.id}: {self.email} ({self.role.value})>"


# ============================================================
# RECURRENCE
# ============================================================

class Recurrence(db.Model):
    __tablename__ = "recurrences"

    id = db.Column(db.Integer, primary_key=True)
    frequency = db.Column(db.String(20), nullable=False, default="WEEKLY")
    occurrences = db.Column(db.Integer, nullable=False, default=1)
    interval = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow_naive)

    events = db.relationship("Event", back_populates="recurrence")
    requests = db.relationship("ResourceRequest", back_populates="recurrence")


class WaitlistStatus(Enum):
    WAITING = "WAITING"
    PROMOTED = "PROMOTED"
    CANCELLED = "CANCELLED"


# ============================================================
# EVENT
# ============================================================

class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(200),
        nullable=False,
    )

    organizer = db.Column(
        db.String(150),
        nullable=False,
    )

    organizer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    expected_attendance = db.Column(
        db.Integer,
        nullable=False,
    )

    start_dt = db.Column(
        db.DateTime,
        nullable=False,
    )

    end_dt = db.Column(
        db.DateTime,
        nullable=False,
    )

    status = db.Column(
        db.Enum(EventStatus),
        nullable=False,
        default=EventStatus.DRAFT,
    )

    recurrence_id = db.Column(
        db.Integer,
        db.ForeignKey("recurrences.id"),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow_naive,
    )

    resource_requests = db.relationship(
        "ResourceRequest",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    allocations = db.relationship(
        "Allocation",
        back_populates="event",
    )

    organizer_user = db.relationship(
        "User",
        back_populates="events",
    )

    recurrence = db.relationship(
        "Recurrence",
        back_populates="events",
    )

    def __repr__(self):
        return f"<Event {self.id}: {self.name}>"


# ============================================================
# RESOURCE
# ============================================================

class Resource(db.Model):
    __tablename__ = "resources"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(150),
        nullable=False,
    )

    type = db.Column(
        db.Enum(ResourceType),
        nullable=False,
    )

    capacity = db.Column(
        db.Integer,
        nullable=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    buffer_minutes = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow_naive,
    )

    allocations = db.relationship(
        "Allocation",
        back_populates="resource",
    )

    request_items = db.relationship(
        "RequestItem",
        back_populates="specific_resource",
    )

    def __repr__(self):
        return f"<Resource {self.id}: {self.name}>"


# ============================================================
# RESOURCE REQUEST
# ============================================================

class ResourceRequest(db.Model):
    __tablename__ = "resource_requests"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False,
    )

    recurrence_id = db.Column(
        db.Integer,
        db.ForeignKey("recurrences.id"),
        nullable=True,
    )

    requested_start = db.Column(
        db.DateTime,
        nullable=False,
    )

    requested_end = db.Column(
        db.DateTime,
        nullable=False,
    )

    status = db.Column(
        db.Enum(RequestStatus),
        nullable=False,
        default=RequestStatus.PENDING,
    )

    # ========================================================
    # REJECTION REASON
    # ========================================================
    #
    # Stores the reason supplied by the administrator when
    # rejecting a resource request.
    #
    # This fixes the previous situation where the route and
    # templates referenced rejection_reason but the database
    # model did not contain the field.
    # ========================================================

    rejection_reason = db.Column(
        db.Text,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow_naive,
    )

    event = db.relationship(
        "Event",
        back_populates="resource_requests",
    )

    recurrence = db.relationship(
        "Recurrence",
        back_populates="requests",
    )

    items = db.relationship(
        "RequestItem",
        back_populates="request",
        cascade="all, delete-orphan",
    )

    allocations = db.relationship(
        "Allocation",
        back_populates="request",
    )

    waitlist_entries = db.relationship(
        "WaitlistEntry",
        back_populates="request",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<ResourceRequest {self.id}>"


# ============================================================
# REQUEST ITEM
# ============================================================

class RequestItem(db.Model):
    __tablename__ = "request_items"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("resource_requests.id"),
        nullable=False,
    )

    resource_type = db.Column(
        db.Enum(ResourceType),
        nullable=False,
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1,
    )

    specific_resource_id = db.Column(
        db.Integer,
        db.ForeignKey("resources.id"),
        nullable=True,
    )

    request = db.relationship(
        "ResourceRequest",
        back_populates="items",
    )

    specific_resource = db.relationship(
        "Resource",
        back_populates="request_items",
    )

    def __repr__(self):
        return (
            f"<RequestItem {self.id}: "
            f"{self.resource_type.value}>"
        )


# ============================================================
# WAITLIST
# ============================================================

class WaitlistEntry(db.Model):
    __tablename__ = "waitlist_entries"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("resource_requests.id"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=True)
    resource_type = db.Column(db.Enum(ResourceType), nullable=False)
    status = db.Column(db.Enum(WaitlistStatus), nullable=False, default=WaitlistStatus.WAITING)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow_naive)
    promoted_at = db.Column(db.DateTime, nullable=True)

    request = db.relationship("ResourceRequest", back_populates="waitlist_entries")
    resource = db.relationship("Resource")

    __table_args__ = (
        db.Index("ix_waitlist_status_type", "status", "resource_type"),
    )


# ============================================================
# ALLOCATION
# ============================================================

class Allocation(db.Model):
    __tablename__ = "allocations"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    resource_id = db.Column(
        db.Integer,
        db.ForeignKey("resources.id"),
        nullable=False,
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False,
    )

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("resource_requests.id"),
        nullable=False,
    )

    start_dt = db.Column(
        db.DateTime,
        nullable=False,
    )

    end_dt = db.Column(
        db.DateTime,
        nullable=False,
    )

    status = db.Column(
        db.Enum(AllocationStatus),
        nullable=False,
        default=AllocationStatus.ALLOCATED,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow_naive,
    )

    resource = db.relationship(
        "Resource",
        back_populates="allocations",
    )

    event = db.relationship(
        "Event",
        back_populates="allocations",
    )

    request = db.relationship(
        "ResourceRequest",
        back_populates="allocations",
    )

    __table_args__ = (
        db.Index(
            "ix_allocation_resource_time",
            "resource_id",
            "start_dt",
            "end_dt",
        ),
    )

    def __repr__(self):
        return f"<Allocation {self.id}>"