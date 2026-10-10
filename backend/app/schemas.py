import re
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Optional, List, Any, Union
from pydantic import BaseModel, Field, field_serializer, model_validator


def _parse_time_str(val: str, default_date: datetime.date) -> datetime:
    val = val.strip()
    # Pure hour integer like "10" or "9"
    if re.match(r"^\d{1,2}$", val):
        hour = int(val)
        if 0 <= hour <= 24:
            if hour == 24:
                return datetime.combine(default_date + timedelta(days=1), time(0, 0), tzinfo=timezone.utc)
            return datetime.combine(default_date, time(hour, 0), tzinfo=timezone.utc)

    # Time-only format like "10:00" or "14:30"
    m_time = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", val)
    if m_time:
        hour = int(m_time.group(1))
        minute = int(m_time.group(2))
        second = int(m_time.group(3)) if m_time.group(3) else 0
        return datetime.combine(default_date, time(hour, minute, second), tzinfo=timezone.utc)

    # Date with hour only, e.g. "2026-10-11T10"
    m_date_hour = re.match(r"^(\d{4}-\d{2}-\d{2})[T ](\d{1,2})$", val)
    if m_date_hour:
        d_str = m_date_hour.group(1)
        hour = int(m_date_hour.group(2))
        return datetime.fromisoformat(f"{d_str}T{hour:02d}:00:00").replace(tzinfo=timezone.utc)

    # Standard ISO string
    clean_val = val.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean_val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    raise ValueError(f"Cannot parse window datetime from '{val}'")


def format_iso_tz(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.isoformat()


def format_time_hms(t: Optional[time]) -> Optional[str]:
    if t is None:
        return None
    return t.strftime("%H:%M:%S")


class Coordinates(BaseModel):
    latitude: float
    longitude: float


# Auth Schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class AgentSummary(BaseModel):
    id: uuid.UUID
    name: str
    shift_start: str
    shift_end: str
    status: str

    @classmethod
    def from_orm_model(cls, agent: Any) -> "AgentSummary":
        return cls(
            id=agent.id,
            name=agent.name,
            shift_start=format_time_hms(agent.shift_start) or "00:00:00",
            shift_end=format_time_hms(agent.shift_end) or "00:00:00",
            status=agent.status,
        )


class AgentWithLocationResponse(BaseModel):
    id: uuid.UUID
    name: str
    shift_start: str
    shift_end: str
    status: str
    current_location: Optional[Coordinates] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 28800
    agent: AgentSummary


# Request Schemas
class CreatePickupRequest(BaseModel):
    customer_name: str = Field(..., max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    address: str = Field(..., max_length=255)
    latitude: float
    longitude: float
    window_start: Union[datetime, str]
    window_end: Union[datetime, str]
    priority: str = "normal"

    @model_validator(mode="before")
    @classmethod
    def parse_and_validate_windows(cls, data: Any) -> Any:
        if isinstance(data, dict):
            ws_val = data.get("window_start")
            we_val = data.get("window_end")

            now = datetime.now(timezone.utc)
            base_date = now.date()

            # If start is time-only and the hour is already past today, roll to tomorrow
            if isinstance(ws_val, str) and (re.match(r"^\d{1,2}$", ws_val.strip()) or re.match(r"^\d{1,2}:\d{2}", ws_val.strip())):
                try:
                    parts = ws_val.strip().split(":")
                    hour = int(parts[0])
                    if hour <= now.hour:
                        base_date = base_date + timedelta(days=1)
                except Exception:
                    pass

            if ws_val is not None:
                if isinstance(ws_val, datetime):
                    ws_dt = ws_val if ws_val.tzinfo else ws_val.replace(tzinfo=timezone.utc)
                else:
                    ws_dt = _parse_time_str(str(ws_val), base_date)
                data["window_start"] = ws_dt

            if we_val is not None:
                end_base_date = (
                    data["window_start"].date()
                    if "window_start" in data and isinstance(data["window_start"], datetime)
                    else base_date
                )
                if isinstance(we_val, datetime):
                    we_dt = we_val if we_val.tzinfo else we_val.replace(tzinfo=timezone.utc)
                else:
                    we_dt = _parse_time_str(str(we_val), end_base_date)
                    if (
                        isinstance(ws_val, str)
                        and not re.search(r"\d{4}-\d{2}-\d{2}", str(we_val))
                        and we_dt <= data.get("window_start", we_dt)
                    ):
                        we_dt = we_dt + timedelta(days=1)
                data["window_end"] = we_dt

        return data


RequestCreate = CreatePickupRequest


class StatusHistoryItem(BaseModel):
    status: str
    timestamp: str


class PickupRequestCreateResponse(BaseModel):
    id: uuid.UUID
    customer_name: str
    phone: Optional[str] = None
    address: str
    latitude: float
    longitude: float
    window_start: str
    window_end: str
    priority: str
    status: str
    assigned_agent_id: Optional[uuid.UUID] = None
    scheduled_time: Optional[str] = None
    unassigned_reason: Optional[str] = None
    created_at: str


class PickupRequestListSummary(BaseModel):
    id: uuid.UUID
    customer_name: str
    status: str
    assigned_agent_id: Optional[uuid.UUID] = None
    scheduled_time: Optional[str] = None
    priority: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    unassigned_reason: Optional[str] = None


class PickupRequestDetailResponse(BaseModel):
    id: uuid.UUID
    customer_name: str
    phone: Optional[str] = None
    address: str
    latitude: float
    longitude: float
    window_start: str
    window_end: str
    priority: str
    status: str
    assigned_agent_id: Optional[uuid.UUID] = None
    scheduled_time: Optional[str] = None
    unassigned_reason: Optional[str] = None
    created_at: str
    status_history: List[StatusHistoryItem] = Field(default_factory=list)


class CancelRequestResponse(BaseModel):
    id: uuid.UUID
    status: str = "Cancelled"
    message: str = "Request cancelled successfully"


class UpdateStatusRequest(BaseModel):
    status: str


class UpdateStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    status_history: List[StatusHistoryItem]


# Agent Schedule Schemas
class AgentScheduleAgent(BaseModel):
    id: uuid.UUID
    name: str


class ScheduleStop(BaseModel):
    request_id: uuid.UUID
    customer_name: str
    address: str
    latitude: float
    longitude: float
    scheduled_time: str
    window_end: str
    status: str
    priority: str = "normal"
    estimated_travel_time_seconds: int
    geometry: Optional[List[List[float]]] = None


class AgentScheduleResponse(BaseModel):
    agent: AgentScheduleAgent
    schedule: List[ScheduleStop]
    total_travel_time_seconds: int
    estimated_times: bool
    geometry: Optional[List[List[float]]] = None


class RouteResponse(BaseModel):
    geometry: List[List[float]]
    distance: float = 0.0
    duration: float = 0.0
    estimated: bool = False



# Scheduler Schemas
class SuggestedSlot(BaseModel):
    agent_id: uuid.UUID
    time: str


class ScheduleDetailItem(BaseModel):
    request_id: uuid.UUID
    action: str
    priority: Optional[str] = "normal"
    assigned_agent_id: Optional[uuid.UUID] = None
    scheduled_time: Optional[str] = None
    reason: Optional[str] = None
    suggested_slot: Optional[SuggestedSlot] = None


class RunScheduleResponse(BaseModel):
    scheduled: int
    unassigned: int
    details: List[ScheduleDetailItem]


# Demo Schemas
class SeedDemoResponse(BaseModel):
    agents_created: int
    requests_created: int


class UrgentRequestSummary(BaseModel):
    id: uuid.UUID
    customer_name: str
    status: str
    priority: str


class UrgentDemoResponse(BaseModel):
    request: UrgentRequestSummary
    affected_agents: List[uuid.UUID]
    bumped_requests: List[uuid.UUID] = Field(default_factory=list)
