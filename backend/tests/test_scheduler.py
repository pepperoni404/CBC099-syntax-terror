import pytest
from datetime import datetime, timezone, timedelta
from app.models import PickupRequest, coords_to_geography
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
