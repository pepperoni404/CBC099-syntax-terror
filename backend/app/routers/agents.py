import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Agent, PickupRequest, geography_to_coords
from app.schemas import (
    AgentWithLocationResponse,
    AgentScheduleResponse,
    AgentScheduleAgent,
    ScheduleStop,
    Coordinates,
    format_time_hms,
    format_iso_tz,
)
from app.auth import get_current_agent, check_agent_assigned
from app.utils.validators import AppException
from app.services.scheduler import get_agent_location, get_request_coords
from app.services.osrm import get_travel_time_matrix, get_route_geometry
from app.config import settings

router = APIRouter(prefix="/agents", tags=["agents"])



@router.get("", response_model=List[AgentWithLocationResponse])
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    results = []
    for a in agents:
        loc = geography_to_coords(a.current_location)
        current_loc = Coordinates(latitude=loc["latitude"], longitude=loc["longitude"]) if loc else None
        results.append(
            AgentWithLocationResponse(
                id=a.id,
                name=a.name,
                shift_start=format_time_hms(a.shift_start) or "00:00:00",
                shift_end=format_time_hms(a.shift_end) or "00:00:00",
                status=a.status,
                current_location=current_loc,
            )
        )
    return results


@router.get("/{id}/schedule", response_model=AgentScheduleResponse)
async def get_agent_schedule(
    id: uuid.UUID,
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    target_agent = db.query(Agent).filter(Agent.id == id).first()
    if not target_agent:
        raise AppException(
            status_code=404,
            code="AGENT_NOT_FOUND",
            message="Agent not found",
        )

    # Authenticated agents can view their own schedule (if agent_id matches URL)
    check_agent_assigned(current_agent, id)

    # Get active pickups in route order
    stops = (
        db.query(PickupRequest)
        .filter(
            PickupRequest.assigned_agent_id == id,
            PickupRequest.status.in_(["Scheduled", "En route", "Picked up"]),
        )
        .order_by(PickupRequest.scheduled_time.asc())
        .all()
    )

    if not stops:
        return AgentScheduleResponse(
            agent=AgentScheduleAgent(id=target_agent.id, name=target_agent.name),
            schedule=[],
            total_travel_time_seconds=0,
            estimated_times=False,
            geometry=[],
        )

    start_loc = get_agent_location(target_agent)
    locations = [start_loc] + [get_request_coords(s) for s in stops]

    matrix_res = await get_travel_time_matrix(locations)
    matrix = matrix_res["matrix"]
    estimated_times = matrix_res["estimated"]

    hub_loc = {"latitude": settings.HUB_LATITUDE, "longitude": settings.HUB_LONGITUDE}

    # Full route waypoints: agent -> pickup1 -> hub -> pickup2 -> hub...
    full_waypoints = [start_loc]
    for s in stops:
        full_waypoints.append(get_request_coords(s))
        full_waypoints.append(hub_loc)

    full_route_res = await get_route_geometry(full_waypoints)
    full_geometry = full_route_res.get("geometry", [])

    schedule_items: List[ScheduleStop] = []
    total_travel_time_seconds = 0

    for i, s in enumerate(stops):
        leg_time = int(round(matrix[i][i + 1]))
        total_travel_time_seconds += leg_time
        coords = get_request_coords(s)

        # Leg geometry: from previous location (agent start or hub) to this pickup
        prev_loc = start_loc if i == 0 else hub_loc
        leg_res = await get_route_geometry([prev_loc, coords])
        leg_geometry = leg_res.get("geometry", [])

        schedule_items.append(
            ScheduleStop(
                request_id=s.id,
                customer_name=s.customer_name,
                address=s.address,
                latitude=coords["latitude"],
                longitude=coords["longitude"],
                scheduled_time=format_iso_tz(s.scheduled_time) or "",
                window_end=format_iso_tz(s.window_end) or "",
                status=s.status,
                priority=s.priority or "normal",
                estimated_travel_time_seconds=leg_time,
                geometry=leg_geometry,
            )
        )

    return AgentScheduleResponse(
        agent=AgentScheduleAgent(id=target_agent.id, name=target_agent.name),
        schedule=schedule_items,
        total_travel_time_seconds=total_travel_time_seconds,
        estimated_times=estimated_times,
        geometry=full_geometry,
    )

