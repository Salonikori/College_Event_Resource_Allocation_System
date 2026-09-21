from datetime import datetime
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


# ============================================================
# EVENT
# ============================================================

class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    organizer = db.Column(db.String(150), nullable=False)
    expected_attendance = db.Column(db.Integer, nullable=False)
    start_dt = db.Column(db.DateTime, nullable=False)
    end_dt = db.Column(db.DateTime, nullable=False)

    status = db.Column(
        db.Enum(EventStatus),
        nullable=False,
        default=EventStatus.DRAFT
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    resource_requests = db.relationship(
        "ResourceRequest",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    allocations = db.relationship(
        "Allocation",
        back_populates="event"
    )

    def __repr__(self):
        return f"<Event {self.id}: {self.name}>"


# ============================================================
# RESOURCE
# ============================================================

class Resource(db.Model):
    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    type = db.Column(db.Enum(ResourceType), nullable=False)
    capacity = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    buffer_minutes = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    allocations = db.relationship(
        "Allocation",
        back_populates="resource"
    )

    request_items = db.relationship(
        "RequestItem",
        back_populates="specific_resource"
    )

    def __repr__(self):
        return f"<Resource {self.id}: {self.name}>"


# ============================================================
# RESOURCE REQUEST
# ============================================================

class ResourceRequest(db.Model):
    __tablename__ = "resource_requests"

    id = db.Column(db.Integer, primary_key=True)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    requested_start = db.Column(
        db.DateTime,
        nullable=False
    )

    requested_end = db.Column(
        db.DateTime,
        nullable=False
    )

    status = db.Column(
        db.Enum(RequestStatus),
        nullable=False,
        default=RequestStatus.PENDING
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    event = db.relationship(
        "Event",
        back_populates="resource_requests"
    )

    items = db.relationship(
        "RequestItem",
        back_populates="request",
        cascade="all, delete-orphan"
    )

    allocations = db.relationship(
        "Allocation",
        back_populates="request"
    )

    def __repr__(self):
        return f"<ResourceRequest {self.id}>"


# ============================================================
# REQUEST ITEM
# ============================================================

class RequestItem(db.Model):
    __tablename__ = "request_items"

    id = db.Column(db.Integer, primary_key=True)

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("resource_requests.id"),
        nullable=False
    )

    resource_type = db.Column(
        db.Enum(ResourceType),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    specific_resource_id = db.Column(
        db.Integer,
        db.ForeignKey("resources.id"),
        nullable=True
    )

    request = db.relationship(
        "ResourceRequest",
        back_populates="items"
    )

    specific_resource = db.relationship(
        "Resource",
        back_populates="request_items"
    )

    def __repr__(self):
        return f"<RequestItem {self.id}: {self.resource_type.value}>"


# ============================================================
# ALLOCATION
# ============================================================

class Allocation(db.Model):
    __tablename__ = "allocations"

    id = db.Column(db.Integer, primary_key=True)

    resource_id = db.Column(
        db.Integer,
        db.ForeignKey("resources.id"),
        nullable=False
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("resource_requests.id"),
        nullable=False
    )

    start_dt = db.Column(
        db.DateTime,
        nullable=False
    )

    end_dt = db.Column(
        db.DateTime,
        nullable=False
    )

    status = db.Column(
        db.Enum(AllocationStatus),
        nullable=False,
        default=AllocationStatus.ALLOCATED
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    resource = db.relationship(
        "Resource",
        back_populates="allocations"
    )

    event = db.relationship(
        "Event",
        back_populates="allocations"
    )

    request = db.relationship(
        "ResourceRequest",
        back_populates="allocations"
    )

    __table_args__ = (
        db.Index(
            "ix_allocation_resource_time",
            "resource_id",
            "start_dt",
            "end_dt"
        ),
    )

    def __repr__(self):
        return f"<Allocation {self.id}>"