import uuid
from datetime import datetime, time
from typing import Optional, List, Any
from sqlalchemy import String, Time, DateTime, ForeignKey, Index, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.compiler import compiles
from geoalchemy2 import Geography, WKTElement
from geoalchemy2.shape import to_shape
from app.database import Base


# Compilation override for SQLite in-memory testing
@compiles(Geography, "sqlite")
def compile_geography_sqlite(type_, compiler, **kw):
    return "TEXT"


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    shift_start: Mapped[time] = mapped_column(Time, nullable=False)
    shift_end: Mapped[time] = mapped_column(Time, nullable=False)
    current_location = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="idle",
    )

    __table_args__ = (
        CheckConstraint("status IN ('idle', 'en route', 'busy')", name="agents_status_check"),
    )

    requests: Mapped[List["PickupRequest"]] = relationship("PickupRequest", back_populates="assigned_agent")


class PickupRequest(Base):
    __tablename__ = "pickup_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="normal",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="Pending",
    )
    assigned_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id"),
        nullable=True,
    )
    scheduled_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    unassigned_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        CheckConstraint("window_end > window_start", name="pickup_requests_window_check"),
        CheckConstraint(
            "priority IN ('urgent', 'normal', 'low')",
            name="pickup_requests_priority_check",
        ),
        CheckConstraint(
            "status IN ('Pending', 'Scheduled', 'En route', 'Picked up', 'Delivered to hub', 'Unassigned', 'Cancelled')",
            name="pickup_requests_status_check",
        ),
        Index("idx_pickup_requests_status", "status"),
        Index("idx_pickup_requests_agent", "assigned_agent_id"),
        Index("idx_pickup_requests_window", "window_start", "window_end"),
    )

    assigned_agent: Mapped[Optional["Agent"]] = relationship("Agent", back_populates="requests")
    status_history: Mapped[List["StatusHistory"]] = relationship(
        "StatusHistory",
        back_populates="request",
        order_by="StatusHistory.timestamp.asc()",
        cascade="all, delete-orphan",
    )


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pickup_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('Pending', 'Scheduled', 'En route', 'Picked up', 'Delivered to hub', 'Unassigned', 'Cancelled')",
            name="status_history_status_check",
        ),
        Index("idx_status_history_request_id", "request_id"),
        Index("idx_status_history_request_timestamp", "request_id", "timestamp"),
    )

    request: Mapped["PickupRequest"] = relationship("PickupRequest", back_populates="status_history")


def coords_to_geography(latitude: float, longitude: float) -> WKTElement:
    """Creates a WKTElement for PostGIS Geography column: POINT(longitude latitude)."""
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


def geography_to_coords(geom: Any) -> Optional[dict]:
    """Extracts {'latitude': lat, 'longitude': lon} from a PostGIS/GeoAlchemy2 geometry."""
    if geom is None:
        return None
    if isinstance(geom, dict):
        if "latitude" in geom and "longitude" in geom:
            return {"latitude": float(geom["latitude"]), "longitude": float(geom["longitude"])}
    if isinstance(geom, str):
        try:
            clean = geom.replace("POINT", "").replace("(", "").replace(")", "").strip()
            parts = clean.split()
            lon, lat = float(parts[0]), float(parts[1])
            return {"latitude": lat, "longitude": lon}
        except Exception:
            return None
    try:
        shape = to_shape(geom)
        return {"latitude": float(shape.y), "longitude": float(shape.x)}
    except Exception:
        try:
            val = str(geom)
            if "POINT" in val:
                clean = val.split("POINT")[1].replace("(", "").replace(")", "").strip()
                parts = clean.split()
                return {"latitude": float(parts[1]), "longitude": float(parts[0])}
        except Exception:
            pass
        return None
