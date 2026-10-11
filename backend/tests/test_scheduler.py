import pytest
from datetime import datetime, timezone, timedelta
from app.models import PickupRequest, coords_to_geography, Agent
from app.services.scheduler import get_effective_priority_tier, run_scheduler
from app.services.demo import seed_demo_data


def test_priority_aging(db):
    now = datetime.now(timezone.utc)

    # 1. Low priority with deadline in 48h -> still low (tier 2)
    req1 = PickupRequest(
        customer_name="R1",
        phone="1",
        address="A",
        location=coords_to_geography(12.9, 77.5),
        window_start=now + timedelta(hours=46),
        window_end=now + timedelta(hours=48),
        priority="low",
    )
    assert get_effective_priority_tier(req1, now) == 2

    # 2. Low priority with deadline in 12h -> promoted to normal (tier 1)
    req2 = PickupRequest(
        customer_name="R2",
        phone="2",
        address="B",
        location=coords_to_geography(12.9, 77.5),
        window_start=now + timedelta(hours=10),
        window_end=now + timedelta(hours=12),
        priority="low",
    )
    assert get_effective_priority_tier(req2, now) == 1

    # 3. Normal priority with deadline in 1.5h -> promoted to urgent (tier 0)
    req3 = PickupRequest(
        customer_name="R3",
        phone="3",
        address="C",
        location=coords_to_geography(12.9, 77.5),
        window_start=now + timedelta(minutes=30),
        window_end=now + timedelta(hours=1, minutes=30),
        priority="normal",
    )
    assert get_effective_priority_tier(req3, now) == 0


@pytest.mark.asyncio
async def test_scheduler_run_and_demo_seed(client, demo_agents, auth_headers, db):
    # 1. Seed demo data
    res_seed = client.post("/demo/seed", headers=auth_headers)
    assert res_seed.status_code == 200
    seed_data = res_seed.json()
    assert seed_data["requests_created"] >= 0

    # 2. Run scheduler
    res_run = client.post("/schedule/run", headers=auth_headers)
    assert res_run.status_code == 200
    data = res_run.json()
    assert "scheduled" in data
    assert "unassigned" in data
    assert "details" in data

    # 3. Check agent schedule
    agent1 = demo_agents[0]
    res_sched = client.get(f"/agents/{agent1.id}/schedule", headers=auth_headers)
    assert res_sched.status_code == 200
    sched_data = res_sched.json()
    assert sched_data["agent"]["name"] == "agent1"
    assert isinstance(sched_data["schedule"], list)
    assert "total_travel_time_seconds" in sched_data
    assert "estimated_times" in sched_data


@pytest.mark.asyncio
async def test_urgent_demo_insertion(client, demo_agents, auth_headers, db):
    # Call /demo/urgent
    res_urgent = client.post("/demo/urgent", headers=auth_headers)
    assert res_urgent.status_code == 200
    urgent_data = res_urgent.json()
    assert urgent_data["request"]["priority"] == "urgent"
    assert "affected_agents" in urgent_data


@pytest.mark.asyncio
async def test_priority_sorting_and_route_order(client, demo_agents, auth_headers, db):
    from datetime import time
    from app.models import StatusHistory
    # Clean previous requests
    db.query(StatusHistory).delete()
    db.query(PickupRequest).delete()
    # Keep only agent1 so all 3 requests are assigned to agent1
    db.query(Agent).filter(Agent.name.in_(["agent2", "agent3"])).delete()
    db.commit()

    now = datetime.now(timezone.utc)
    base_date = now.date() + timedelta(days=1)
    w_start = datetime.combine(base_date, time(10, 0), tzinfo=timezone.utc)
    w_end = datetime.combine(base_date, time(12, 0), tzinfo=timezone.utc)

    # Submit low first, then normal, then urgent to test priority ordering over creation order
    r_low = client.post("/requests", json={
        "customer_name": "Low Customer",
        "address": "88 Residency Road",
        "latitude": 12.9650,
        "longitude": 77.6010,
        "window_start": w_start.isoformat(),
        "window_end": w_end.isoformat(),
        "priority": "low",
    })
    assert r_low.status_code == 201

    r_normal = client.post("/requests", json={
        "customer_name": "Normal Customer",
        "address": "100 MG Road",
        "latitude": 12.9750,
        "longitude": 77.5980,
        "window_start": w_start.isoformat(),
        "window_end": w_end.isoformat(),
        "priority": "normal",
    })
    assert r_normal.status_code == 201

    r_urgent = client.post("/requests", json={
        "customer_name": "Urgent Customer",
        "address": "45 Brigade Road",
        "latitude": 12.9690,
        "longitude": 77.5920,
        "window_start": w_start.isoformat(),
        "window_end": w_end.isoformat(),
        "priority": "urgent",
    })
    assert r_urgent.status_code == 201

    # Reset requests to Pending to test batch run_scheduler priority sorting
    db.query(PickupRequest).update({
        PickupRequest.status: "Pending",
        PickupRequest.assigned_agent_id: None,
        PickupRequest.scheduled_time: None,
    })
    db.commit()

    # Run scheduler
    res_run = client.post("/schedule/run", headers=auth_headers)
    assert res_run.status_code == 200
    data = res_run.json()
    details = data["details"]

    # Scheduler output: Urgent assigned first, then normal, then low
    assert len(details) == 3
    assert details[0]["priority"] == "urgent"
    assert details[1]["priority"] == "normal"
    assert details[2]["priority"] == "low"

    # Agent schedule: Urgent appears first in the route
    assigned_agent_id = details[0]["assigned_agent_id"]
    res_sched = client.get(f"/agents/{assigned_agent_id}/schedule", headers=auth_headers)
    assert res_sched.status_code == 200
    sched_data = res_sched.json()
    schedule_stops = sched_data["schedule"]
    assert len(schedule_stops) == 3
    assert schedule_stops[0]["customer_name"] == "Urgent Customer"
    assert schedule_stops[0]["priority"] == "urgent"
