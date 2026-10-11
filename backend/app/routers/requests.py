import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Agent, PickupRequest, StatusHistory, coords_to_geography, geography_to_coords
from app.schemas import (
    CreatePickupRequest,
    PickupRequestCreateResponse,
    PickupRequestListSummary,
    PickupRequestDetailResponse,
    CancelRequestResponse,
    UpdateStatusRequest,
    UpdateStatusResponse,
    StatusHistoryItem,
    format_iso_tz,
)
from app.auth import get_current_agent
from app.utils.validators import (
    AppException,
    validate_coordinates,
    validate_priority,
    validate_window,
    validate_agent_shift_overlap,
    validate_status_transition,
)
from app.services.scheduler import run_scheduler, insert_urgent_request

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("", response_model=PickupRequestCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_pickup_request(payload: CreatePickupRequest, db: Session = Depends(get_db)):
    # 1. Validation
    validate_coordinates(payload.latitude, payload.longitude)
    validate_priority(payload.priority)
    validate_window(payload.window_start, payload.window_end)
    validate_agent_shift_overlap(payload.window_start, payload.window_end, db)

    now = datetime.now(timezone.utc)
    ws = payload.window_start if payload.window_start.tzinfo else payload.window_start.replace(tzinfo=timezone.utc)
    we = payload.window_end if payload.window_end.tzinfo else payload.window_end.replace(tzinfo=timezone.utc)

    # 2. Create Model
    new_request = PickupRequest(
        customer_name=payload.customer_name,
        phone=payload.phone,
        address=payload.address,
        location=coords_to_geography(payload.latitude, payload.longitude),
        window_start=ws,
        window_end=we,
        priority=payload.priority.lower(),
        status="Pending",
        assigned_agent_id=None,
        scheduled_time=None,
        unassigned_reason=None,
        created_at=now,
    )
    db.add(new_request)
    db.flush()

    # Initial status history
    history = StatusHistory(
        request_id=new_request.id,
        status="Pending",
        timestamp=now,
    )
    db.add(history)
    db.commit()

    # Automatically trigger scheduler to assign to agent
    if new_request.priority.lower() == "urgent":
        await insert_urgent_request(db, new_request)
    else:
        await run_scheduler(db)

    db.refresh(new_request)

    return PickupRequestCreateResponse(
        id=new_request.id,
        customer_name=new_request.customer_name,
        phone=new_request.phone,
        address=new_request.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        window_start=format_iso_tz(new_request.window_start),
        window_end=format_iso_tz(new_request.window_end),
        priority=new_request.priority,
        status=new_request.status,
        assigned_agent_id=new_request.assigned_agent_id,
        scheduled_time=format_iso_tz(new_request.scheduled_time),
        unassigned_reason=new_request.unassigned_reason,
        created_at=format_iso_tz(new_request.created_at),
    )


@router.get("", response_model=List[PickupRequestListSummary])
def list_pickup_requests(
    status: Optional[str] = Query(None),
    agent_id: Optional[uuid.UUID] = Query(None),
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(PickupRequest)
    if status:
        query = query.filter(func.lower(PickupRequest.status) == status.strip().lower())
    if agent_id:
        query = query.filter(PickupRequest.assigned_agent_id == agent_id)
    if date:
        try:
            target_date = datetime.strptime(date.strip(), "%Y-%m-%d").date()
            query = query.filter(
                (func.date(PickupRequest.window_start) == target_date)
                | (func.date(PickupRequest.scheduled_time) == target_date)
            )
        except ValueError:
            pass

    records = query.order_by(PickupRequest.created_at.asc()).all()
    results = []
    for r in records:
        coords = geography_to_coords(r.location) if r.location else None
        results.append(
            PickupRequestListSummary(
                id=r.id,
                customer_name=r.customer_name,
                status=r.status,
                assigned_agent_id=r.assigned_agent_id,
                scheduled_time=format_iso_tz(r.scheduled_time),
                priority=r.priority,
                latitude=coords["latitude"] if coords else None,
                longitude=coords["longitude"] if coords else None,
                address=r.address,
                window_start=format_iso_tz(r.window_start),
                window_end=format_iso_tz(r.window_end),
                unassigned_reason=r.unassigned_reason,
            )
        )
    return results


@router.get("/{id}", response_model=PickupRequestDetailResponse)
def get_pickup_request_detail(id: uuid.UUID, db: Session = Depends(get_db)):
    req = db.query(PickupRequest).filter(PickupRequest.id == id).first()
    if not req:
        raise AppException(
            status_code=404,
            code="REQUEST_NOT_FOUND",
            message="Pickup request not found",
        )

    coords = geography_to_coords(req.location) or {"latitude": 0.0, "longitude": 0.0}
    history_items = [
        StatusHistoryItem(
            status=h.status,
            timestamp=format_iso_tz(h.timestamp) or "",
        )
        for h in req.status_history
    ]

    return PickupRequestDetailResponse(
        id=req.id,
        customer_name=req.customer_name,
        phone=req.phone,
        address=req.address,
        latitude=coords["latitude"],
        longitude=coords["longitude"],
        window_start=format_iso_tz(req.window_start) or "",
        window_end=format_iso_tz(req.window_end) or "",
        priority=req.priority,
        status=req.status,
        assigned_agent_id=req.assigned_agent_id,
        scheduled_time=format_iso_tz(req.scheduled_time),
        unassigned_reason=req.unassigned_reason,
        created_at=format_iso_tz(req.created_at) or "",
        status_history=history_items,
    )


@router.patch("/{id}/cancel", response_model=CancelRequestResponse)
def cancel_pickup_request(id: uuid.UUID, db: Session = Depends(get_db)):
    req = db.query(PickupRequest).filter(PickupRequest.id == id).first()
    if not req:
        raise AppException(
            status_code=404,
            code="REQUEST_NOT_FOUND",
            message="Pickup request not found",
        )

    if req.status in ["En route", "Picked up", "Delivered to hub", "Cancelled"]:
        raise AppException(
            status_code=409,
            code="INVALID_TRANSITION",
            message="Cannot cancel a request that is already En route, Picked up, or Delivered",
        )

    req.status = "Cancelled"
    req.assigned_agent_id = None
    req.scheduled_time = None

    now = datetime.now(timezone.utc)
    db.add(StatusHistory(request_id=req.id, status="Cancelled", timestamp=now))
    db.commit()

    return CancelRequestResponse(
        id=req.id,
        status="Cancelled",
        message="Request cancelled successfully",
    )


@router.patch("/{id}/status", response_model=UpdateStatusResponse)
def update_pickup_request_status(
    id: uuid.UUID,
    payload: UpdateStatusRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    req = db.query(PickupRequest).filter(PickupRequest.id == id).first()
    if not req:
        raise AppException(
            status_code=404,
            code="REQUEST_NOT_FOUND",
            message="Pickup request not found",
        )

    target_status = payload.status.strip()

    # If transitioning to En route, Picked up, Delivered to hub: agent must be assigned
    if target_status in ["En route", "Picked up", "Delivered to hub"]:
        if req.assigned_agent_id != current_agent.id:
            raise AppException(
                status_code=403,
                code="NOT_ASSIGNED",
                message="You are not assigned to this request",
            )

    validate_status_transition(req.status, target_status)

    req.status = target_status
    now = datetime.now(timezone.utc)

    # Update agent state
    if target_status == "En route":
        current_agent.status = "en route"
        if req.location:
            current_agent.current_location = req.location
    elif target_status == "Picked up":
        current_agent.status = "busy"
        if req.location:
            current_agent.current_location = req.location
    elif target_status == "Delivered to hub":
        # Check if agent has remaining active pickups
        remaining = (
            db.query(PickupRequest)
            .filter(
                PickupRequest.assigned_agent_id == current_agent.id,
                PickupRequest.id != req.id,
                PickupRequest.status.in_(["En route", "Picked up"]),
            )
            .count()
        )
        if remaining == 0:
            current_agent.status = "idle"

    db.add(StatusHistory(request_id=req.id, status=target_status, timestamp=now))
    db.commit()
    db.refresh(req)

    history_items = [
        StatusHistoryItem(
            status=h.status,
            timestamp=format_iso_tz(h.timestamp) or "",
        )
        for h in req.status_history
    ]

    return UpdateStatusResponse(
        id=req.id,
        status=req.status,
        status_history=history_items,
    )
