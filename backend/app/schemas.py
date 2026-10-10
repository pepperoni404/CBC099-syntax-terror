import uuid
from datetime import datetime, time
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_serializer


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
    phone: str = Field(..., max_length=20)
    address: str = Field(..., max_length=255)
    latitude: float
    longitude: float
    window_start: datetime
    window_end: datetime
    priority: str = "normal"


class StatusHistoryItem(BaseModel):
    status: str
    timestamp: str


class PickupRequestCreateResponse(BaseModel):
    id: uuid.UUID
    customer_name: str
    phone: str
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
    phone: str
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
