from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Agent


class AppException(Exception):
    def __init__(self, status_code: int, code: str, message: str, field: Optional[str] = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field
        super().__init__(message)


def validate_coordinates(latitude: float, longitude: float):
    if latitude < -90.0 or latitude > 90.0:
        raise AppException(
            status_code=400,
            code="INVALID_COORDINATES",
            message="latitude must be between -90 and 90",
            field="latitude",
        )
    if longitude < -180.0 or longitude > 180.0:
        raise AppException(
            status_code=400,
            code="INVALID_COORDINATES",
            message="longitude must be between -180 and 180",
            field="longitude",
        )


def validate_priority(priority: str):
    valid_priorities = ("urgent", "normal", "low")
    if priority.lower() not in valid_priorities:
        raise AppException(
            status_code=400,
            code="INVALID_PRIORITY",
            message="priority must be one of: urgent, normal, low",
            field="priority",
        )


def validate_window(window_start: datetime, window_end: datetime):
    # Ensure UTC timezone awareness
    now = datetime.now(timezone.utc)
    ws = window_start if window_start.tzinfo else window_start.replace(tzinfo=timezone.utc)
    we = window_end if window_end.tzinfo else window_end.replace(tzinfo=timezone.utc)

    if we <= ws:
        raise AppException(
            status_code=400,
            code="INVALID_WINDOW",
            message="window_end must be after window_start",
            field="window_end",
        )

    duration = we - ws
    if duration < timedelta(minutes=59):
        raise AppException(
            status_code=400,
            code="INVALID_WINDOW",
            message="Window duration must be at least 1 hour",
            field="window_end",
        )

    if duration > timedelta(hours=8, minutes=1):
        raise AppException(
            status_code=400,
            code="INVALID_WINDOW",
            message="Window duration cannot exceed 8 hours",
            field="window_end",
        )

    if ws < now:
        raise AppException(
            status_code=400,
            code="WINDOW_IN_PAST",
            message="window_start must be in the future",
            field="window_start",
        )


def validate_agent_shift_overlap(window_start: datetime, window_end: datetime, db: Session):
    ws = window_start if window_start.tzinfo else window_start.replace(tzinfo=timezone.utc)
    we = window_end if window_end.tzinfo else window_end.replace(tzinfo=timezone.utc)

    agents = db.query(Agent).all()
    if not agents:
        raise AppException(
            status_code=400,
            code="NO_AGENT_AVAILABLE",
            message="No agent is available during the requested time window",
            field="window_start",
        )

    # Check across dates spanned by the window
    start_date = ws.date()
    end_date = we.date()

    has_overlap = False
    for agent in agents:
        cur_date = start_date
        while cur_date <= end_date:
            shift_start_dt = datetime.combine(cur_date, agent.shift_start, tzinfo=timezone.utc)
            shift_end_dt = datetime.combine(cur_date, agent.shift_end, tzinfo=timezone.utc)

            # Check overlap between [ws, we] and [shift_start_dt, shift_end_dt]
            overlap_start = max(ws, shift_start_dt)
            overlap_end = min(we, shift_end_dt)
            if overlap_start < overlap_end:
                has_overlap = True
                break
            cur_date += timedelta(days=1)
        if has_overlap:
            break

    if not has_overlap:
        raise AppException(
            status_code=400,
            code="NO_AGENT_AVAILABLE",
            message="No agent is available during the requested time window",
            field="window_start",
        )


ALLOWED_TRANSITIONS = {
    "Scheduled": ["En route", "Cancelled"],
    "En route": ["Picked up", "Cancelled"],
    "Picked up": ["Delivered to hub"],
    "Pending": ["Cancelled"],
    "Unassigned": ["Cancelled", "Scheduled"],
}


def validate_status_transition(current_status: str, new_status: str):
    allowed = ALLOWED_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise AppException(
            status_code=409,
            code="INVALID_TRANSITION",
            message=f"Cannot transition from {current_status} to {new_status}",
        )
