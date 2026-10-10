from datetime import datetime, timezone, timedelta, time
from typing import Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from app.models import Agent, PickupRequest, StatusHistory, coords_to_geography
from app.auth import hash_password
from app.config import settings
from app.services.scheduler import insert_urgent_request, run_scheduler


def seed_demo_data(db: Session, reset: bool = False) -> Tuple[int, int]:
    """
    Seeds demo agents and requests per Section 8.
    Idempotent: safe to run multiple times.
    """
    if reset:
        db.query(StatusHistory).delete()
        db.query(PickupRequest).delete()
        # Reset existing agents status and location instead of deleting to preserve active auth tokens
        for a in db.query(Agent).all():
            a.status = "idle"
        db.commit()

    agents_created = 0
    requests_created = 0

    # 1. Seed Agents
    existing_agents = {a.name: a for a in db.query(Agent).all()}

    demo_agents_spec = [
        {"name": "agent1", "password": "courier123", "shift_start": time(8, 0), "shift_end": time(17, 0), "lat": 12.9716, "lon": 77.5946},
        {"name": "agent2", "password": "courier123", "shift_start": time(8, 0), "shift_end": time(17, 0), "lat": 12.9750, "lon": 77.5900},
        {"name": "agent3", "password": "courier123", "shift_start": time(9, 0), "shift_end": time(18, 0), "lat": 12.9680, "lon": 77.6000},
    ]

    for spec in demo_agents_spec:
        if spec["name"] not in existing_agents:
            agent = Agent(
                name=spec["name"],
                password_hash=hash_password(spec["password"]),
                shift_start=spec["shift_start"],
                shift_end=spec["shift_end"],
                status="idle",
                current_location=coords_to_geography(spec["lat"], spec["lon"]),
            )
            db.add(agent)
            agents_created += 1
        else:
            existing_agent = existing_agents[spec["name"]]
            existing_agent.current_location = coords_to_geography(spec["lat"], spec["lon"])
            existing_agent.password_hash = hash_password(spec["password"])
            existing_agent.status = "idle"
            if reset:
                agents_created += 1


    db.commit()

    # 2. Seed Pickups
    now = datetime.now(timezone.utc)
    base_date = now.date()
    # If today's working shift has passed or is near the end, schedule for tomorrow
    if now.hour >= 15:
        base_date = base_date + timedelta(days=1)

    demo_requests_spec = [
        {
            "customer_name": "Aarav Sharma",
            "phone": "+919876543210",
            "address": "100 MG Road, Bangalore",
            "lat": 12.9750,
            "lon": 77.5980,
            "start_hour": 10,
            "start_min": 0,
            "end_hour": 12,
            "end_min": 0,
            "priority": "normal",
        },
        {
            "customer_name": "Priya Patel",
            "phone": "+919876543211",
            "address": "45 Brigade Road, Bangalore",
            "lat": 12.9690,
            "lon": 77.5920,
            "start_hour": 10,
            "start_min": 30,
            "end_hour": 12,
            "end_min": 30,
            "priority": "urgent",
        },
        {
            "customer_name": "Rahul Verma",
            "phone": "+919876543212",
            "address": "12 Commercial Street, Bangalore",
            "lat": 12.9800,
            "lon": 77.6050,
            "start_hour": 11,
            "start_min": 0,
            "end_hour": 13,
            "end_min": 0,
            "priority": "low",
        },
        {
            "customer_name": "Sneha Rao",
            "phone": "+919876543213",
            "address": "88 Residency Road, Bangalore",
            "lat": 12.9650,
            "lon": 77.6010,
            "start_hour": 13,
            "start_min": 30,
            "end_hour": 15,
            "end_min": 30,
            "priority": "normal",
        },
        {
            "customer_name": "Vikram Malhotra",
            "phone": "+919876543214",
            "address": "22 Cunningham Road, Bangalore",
            "lat": 12.9720,
            "lon": 77.5890,
            "start_hour": 14,
            "start_min": 0,
            "end_hour": 16,
            "end_min": 0,
            "priority": "urgent",
        },
        {
            "customer_name": "Ananya Iyer",
            "phone": "+919876543215",
            "address": "60 Lavelle Road, Bangalore",
            "lat": 12.9780,
            "lon": 77.5930,
            "start_hour": 14,
            "start_min": 30,
            "end_hour": 16,
            "end_min": 30,
            "priority": "normal",
        },
    ]

    for req_spec in demo_requests_spec:
        # Check if already exists by customer_name
        existing = db.query(PickupRequest).filter(PickupRequest.customer_name == req_spec["customer_name"]).first()
        if not existing:
            w_start = datetime.combine(base_date, time(req_spec["start_hour"], req_spec["start_min"]), tzinfo=timezone.utc)
            w_end = datetime.combine(base_date, time(req_spec["end_hour"], req_spec["end_min"]), tzinfo=timezone.utc)

            # Ensure w_start is in the future
            if w_start < now:
                w_start = now + timedelta(hours=1)
                w_end = w_start + timedelta(hours=2)

            req = PickupRequest(
                customer_name=req_spec["customer_name"],
                phone=req_spec["phone"],
                address=req_spec["address"],
                location=coords_to_geography(req_spec["lat"], req_spec["lon"]),
                window_start=w_start,
                window_end=w_end,
                priority=req_spec["priority"],
                status="Pending",
            )
            db.add(req)
            db.flush()
            hist = StatusHistory(
                request_id=req.id,
                status="Pending",
                timestamp=now,
            )
            db.add(hist)
            requests_created += 1

    db.commit()
    return agents_created, requests_created


async def create_urgent_demo_request(db: Session) -> Dict[str, Any]:
    """Creates an urgent request near the hub and triggers urgent insertion."""
    now = datetime.now(timezone.utc)
    w_start = now + timedelta(minutes=10)
    w_end = now + timedelta(hours=2)

    urgent_req = PickupRequest(
        customer_name="Arjun Kumar",
        phone="+919999999999",
        address="10 Vittal Mallya Road, Bangalore",
        location=coords_to_geography(12.9730, 77.5960),
        window_start=w_start,
        window_end=w_end,
        priority="urgent",
        status="Pending",
    )
    db.add(urgent_req)
    db.flush()
    db.add(StatusHistory(request_id=urgent_req.id, status="Pending", timestamp=now))
    db.commit()

    updated_req, affected_agents, bumped_requests = await insert_urgent_request(db, urgent_req)

    return {
        "request": {
            "id": updated_req.id,
            "customer_name": updated_req.customer_name,
            "status": updated_req.status,
            "priority": updated_req.priority,
        },
        "affected_agents": affected_agents,
        "bumped_requests": bumped_requests,
    }
