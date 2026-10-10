from datetime import datetime, timezone, timedelta
from app.models import PickupRequest, StatusHistory, coords_to_geography
from app.auth import create_access_token


def test_create_request_success(client, demo_agents):
    now = datetime.now(timezone.utc)
    # Ensure tomorrow 10:00 to 12:00 within agent shift
    tomorrow = now.date() + timedelta(days=1)
    w_start = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=10)
    w_end = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12)

    payload = {
        "customer_name": "Test Customer",
        "phone": "+1234567890",
        "address": "123 Main St",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "window_start": w_start.isoformat(),
        "window_end": w_end.isoformat(),
        "priority": "normal",
    }
    response = client.post("/requests", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] == "Test Customer"
    assert data["status"] == "Pending"
    assert data["assigned_agent_id"] is None
    assert data["scheduled_time"] is None
    assert data["priority"] == "normal"
    assert data["latitude"] == 12.9716
    assert data["longitude"] == 77.5946


def test_create_request_invalid_window(client, demo_agents):
    now = datetime.now(timezone.utc)
    w_start = now + timedelta(hours=5)
    w_end = now + timedelta(hours=4)  # end before start

    payload = {
        "customer_name": "Test",
        "phone": "+1234567890",
        "address": "123 Main St",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "window_start": w_start.isoformat(),
        "window_end": w_end.isoformat(),
        "priority": "normal",
    }
    response = client.post("/requests", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "INVALID_WINDOW"
    assert err.get("field") == "window_end"


def test_create_request_window_in_past(client, demo_agents):
    now = datetime.now(timezone.utc)
    w_start = now - timedelta(hours=2)
    w_end = now + timedelta(hours=1)

    payload = {
        "customer_name": "Test",
        "phone": "+1234567890",
        "address": "123 Main St",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "window_start": w_start.isoformat(),
        "window_end": w_end.isoformat(),
        "priority": "normal",
    }
    response = client.post("/requests", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "WINDOW_IN_PAST"
    assert err.get("field") == "window_start"


def test_create_request_invalid_coordinates(client, demo_agents):
    now = datetime.now(timezone.utc)
    w_start = now + timedelta(hours=2)
    w_end = now + timedelta(hours=4)

    payload = {
        "customer_name": "Test",
        "phone": "+1234567890",
        "address": "123 Main St",
        "latitude": 95.0,  # Invalid
        "longitude": 77.5946,
        "window_start": w_start.isoformat(),
        "window_end": w_end.isoformat(),
        "priority": "normal",
    }
    response = client.post("/requests", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "INVALID_COORDINATES"


def test_create_request_invalid_priority(client, demo_agents):
    now = datetime.now(timezone.utc)
    w_start = now + timedelta(hours=2)
    w_end = now + timedelta(hours=4)

    payload = {
        "customer_name": "Test",
        "phone": "+1234567890",
        "address": "123 Main St",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "window_start": w_start.isoformat(),
        "window_end": w_end.isoformat(),
        "priority": "superfast",  # Invalid
    }
    response = client.post("/requests", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "INVALID_PRIORITY"


def test_create_request_no_agent_available(client, demo_agents):
    now = datetime.now(timezone.utc)
    tomorrow = now.date() + timedelta(days=1)
    # 01:00 to 03:00 at night (no shift active)
    w_start = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1)
    w_end = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=3)

    payload = {
        "customer_name": "Test Night",
        "phone": "+1234567890",
        "address": "123 Main St",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "window_start": w_start.isoformat(),
        "window_end": w_end.isoformat(),
        "priority": "normal",
    }
    response = client.post("/requests", json=payload)
    assert response.status_code == 400
    err = response.json().get("error", {})
    assert err.get("code") == "NO_AGENT_AVAILABLE"


def test_get_and_cancel_request(client, demo_agents, db):
    now = datetime.now(timezone.utc)
    req = PickupRequest(
        customer_name="Cancel Test",
        phone="+1234567890",
        address="123 Cancel St",
        location=coords_to_geography(12.9716, 77.5946),
        window_start=now + timedelta(hours=1),
        window_end=now + timedelta(hours=3),
        priority="normal",
        status="Pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # 1. Get Detail
    res_get = client.get(f"/requests/{req.id}")
    assert res_get.status_code == 200
    assert res_get.json()["customer_name"] == "Cancel Test"

    # 2. Cancel
    res_cancel = client.patch(f"/requests/{req.id}/cancel")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "Cancelled"

    # 3. Cannot cancel again
    res_cancel_again = client.patch(f"/requests/{req.id}/cancel")
    assert res_cancel_again.status_code == 409
    assert res_cancel_again.json()["error"]["code"] == "INVALID_TRANSITION"


def test_status_transitions_and_auth(client, demo_agents, db):
    agent1 = demo_agents[0]
    agent2 = demo_agents[1]
    token1, _ = create_access_token(str(agent1.id), agent1.name)
    token2, _ = create_access_token(str(agent2.id), agent2.name)

    now = datetime.now(timezone.utc)
    req = PickupRequest(
        customer_name="Status Test",
        phone="+1234567890",
        address="123 Status St",
        location=coords_to_geography(12.9716, 77.5946),
        window_start=now + timedelta(hours=1),
        window_end=now + timedelta(hours=3),
        priority="normal",
        status="Scheduled",
        assigned_agent_id=agent1.id,
        scheduled_time=now + timedelta(hours=1, minutes=30),
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # Agent 2 attempts transition -> 403 NOT_ASSIGNED
    res_agent2 = client.patch(
        f"/requests/{req.id}/status",
        headers={"Authorization": f"Bearer {token2}"},
        json={"status": "En route"},
    )
    assert res_agent2.status_code == 403
    assert res_agent2.json()["error"]["code"] == "NOT_ASSIGNED"

    # Agent 1 transitions Scheduled -> En route
    res_agent1 = client.patch(
        f"/requests/{req.id}/status",
        headers={"Authorization": f"Bearer {token1}"},
        json={"status": "En route"},
    )
    assert res_agent1.status_code == 200
    assert res_agent1.json()["status"] == "En route"

    # En route -> Delivered to hub (invalid transition, must go to Picked up first)
    res_invalid = client.patch(
        f"/requests/{req.id}/status",
        headers={"Authorization": f"Bearer {token1}"},
        json={"status": "Delivered to hub"},
    )
    assert res_invalid.status_code == 409
    assert res_invalid.json()["error"]["code"] == "INVALID_TRANSITION"

    # En route -> Picked up
    res_pickup = client.patch(
        f"/requests/{req.id}/status",
        headers={"Authorization": f"Bearer {token1}"},
        json={"status": "Picked up"},
    )
    assert res_pickup.status_code == 200
    assert res_pickup.json()["status"] == "Picked up"

    # Picked up -> Delivered to hub
    res_delivered = client.patch(
        f"/requests/{req.id}/status",
        headers={"Authorization": f"Bearer {token1}"},
        json={"status": "Delivered to hub"},
    )
    assert res_delivered.status_code == 200
    assert res_delivered.json()["status"] == "Delivered to hub"
