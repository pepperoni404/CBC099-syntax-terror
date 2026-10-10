def test_login_success(client, demo_agents):
    response = client.post(
        "/auth/login",
        json={"username": "agent1", "password": "courier123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 28800
    assert data["agent"]["name"] == "agent1"
    assert data["agent"]["status"] == "idle"
    assert data["agent"]["shift_start"] == "08:00:00"
    assert data["agent"]["shift_end"] == "17:00:00"


def test_login_invalid_password(client, demo_agents):
    response = client.post(
        "/auth/login",
        json={"username": "agent1", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    err = response.json().get("error", {})
    assert err.get("code") == "INVALID_CREDENTIALS"
    assert err.get("message") == "Invalid username or password"


def test_login_nonexistent_user(client, demo_agents):
    response = client.post(
        "/auth/login",
        json={"username": "ghost_agent", "password": "courier123"},
    )
    assert response.status_code == 401
    err = response.json().get("error", {})
    assert err.get("code") == "INVALID_CREDENTIALS"


def test_get_me_success(client, auth_headers):
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "agent1"
    assert data["status"] == "idle"


def test_get_me_no_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    err = response.json().get("error", {})
    assert err.get("code") == "NOT_AUTHENTICATED"


def test_get_me_invalid_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert response.status_code == 401
    err = response.json().get("error", {})
    assert err.get("code") == "NOT_AUTHENTICATED"
