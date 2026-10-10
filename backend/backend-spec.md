# Backend Specification: Smart Courier Pickup Scheduling System

**Date:** 2026-10-10
**Status:** Draft for review

---

## 1. Architecture Overview

`
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                            │
│  (Customer Form / Tracking / Dispatcher Map / Agent Dashboard)   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP (REST, JSON)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Auth    │  │ Requests │  │  Agent   │  │   Scheduler   │  │
│  │  Router  │  │  Router  │  │  Router  │  │   Engine      │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬───────┘  │
│       │              │              │                │           │
│       └──────────────┴──────────────┴────────────────┘           │
│                              │                                    │
│                    ┌─────────┴─────────┐                         │
│                    │   SQLAlchemy ORM   │                         │
│                    └─────────┬─────────┘                         │
└──────────────────────────────┼──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
     │  PostgreSQL  │  │    OSRM      │  │   Config     │
     │  + PostGIS   │  │  (external)  │  │  (env vars)  │
     └──────────────┘  └──────────────┘  └──────────────┘
`

### Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Runtime | Python | 3.11+ |
| Web Framework | FastAPI | Latest stable |
| ORM | SQLAlchemy | 2.x |
| Database | PostgreSQL | 15+ |
| Spatial | PostGIS | 3.x |
| Auth | PyJWT + bcrypt | Latest |
| HTTP Client | httpx | Latest (async) |
| Validation | Pydantic | 2.x |

---

## 2. Database Schema

### 2.1 Entity Relationship Diagram

`
┌──────────────────────┐         ┌──────────────────────────┐
│       agents         │         │    pickup_requests       │
├──────────────────────┤         ├──────────────────────────┤
│ id (UUID, PK)        │◄────────┤ assigned_agent_id (FK)   │
│ name (VARCHAR)       │    1:N  │ id (UUID, PK)            │
│ password_hash (VARCHAR)        │ customer_name (VARCHAR)  │
│ shift_start (TIME)   │         │ phone (VARCHAR)          │
│ shift_end (TIME)     │         │ address (VARCHAR)        │
│ current_location    │         │ location (GEOGRAPHY)     │
│   (GEOGRAPHY POINT)  │         │ window_start (TIMESTAMPTZ)│
│ status (VARCHAR)     │         │ window_end (TIMESTAMPTZ) │
└──────────────────────┘         │ priority (VARCHAR)      │
                                 │ status (VARCHAR)        │
┌──────────────────────┐         │ scheduled_time (TIMESTAMPTZ)│
│   status_history     │         │ unassigned_reason        │
├──────────────────────┤         │   (VARCHAR, nullable)   │
│ id (UUID, PK)        │         │ created_at (TIMESTAMPTZ) │
│ request_id (UUID, FK)│────────►│                          │
│ status (VARCHAR)     │    1:N  └──────────────────────────┘
│ timestamp (TIMESTAMPTZ)        │
└──────────────────────┘
`

### 2.2 Table Definitions

#### agents

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() |
| name | VARCHAR(100) | NOT NULL |
| password_hash | VARCHAR(255) | NOT NULL |
| shift_start | TIME | NOT NULL |
| shift_end | TIME | NOT NULL |
| current_location | GEOGRAPHY(POINT, 4326) | NULL |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'idle', CHECK (status IN ('idle', 'en route', 'busy')) |

**Indexes:**
- Primary key on id

#### pickup_requests

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() |
| customer_name | VARCHAR(100) | NOT NULL |
| phone | VARCHAR(20) | NOT NULL |
| address | VARCHAR(255) | NOT NULL |
| location | GEOGRAPHY(POINT, 4326) | NOT NULL |
| window_start | TIMESTAMPTZ | NOT NULL |
| window_end | TIMESTAMPTZ | NOT NULL, CHECK (window_end > window_start) |
| priority | VARCHAR(10) | NOT NULL, DEFAULT 'normal', CHECK (priority IN ('urgent', 'normal', 'low')) |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'Pending', CHECK (status IN ('Pending', 'Scheduled', 'En route', 'Picked up', 'Delivered to hub', 'Unassigned', 'Cancelled')) |
| assigned_agent_id | UUID | FOREIGN KEY REFERENCES agents(id), NULL |
| scheduled_time | TIMESTAMPTZ | NULL |
| unassigned_reason | VARCHAR(255) | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |

**Indexes:**
- Primary key on id
- B-tree on status
- B-tree on ssigned_agent_id
- B-tree on (window_start, window_end)
- GiST spatial index on location

#### status_history

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() |
| request_id | UUID | NOT NULL, FOREIGN KEY REFERENCES pickup_requests(id) |
| status | VARCHAR(20) | NOT NULL, CHECK (status IN ('Pending', 'Scheduled', 'En route', 'Picked up', 'Delivered to hub', 'Unassigned', 'Cancelled')) |
| timestamp | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |

**Indexes:**
- Primary key on id
- B-tree on equest_id
- B-tree on (request_id, timestamp) for history retrieval

### 2.3 Hub Configuration

The hub is a single fixed point stored in configuration, not a database table.

`python
# config.py
HUB_LOCATION = {
    "latitude": float(os.getenv("HUB_LATITUDE", "12.9716")),
    "longitude": float(os.getenv("HUB_LONGITUDE", "77.5946"))
}
`

---

## 3. API Specification

### 3.1 Authentication

#### POST /auth/login

Authenticate an agent and return a JWT token.

**Request:**
`json
{
  "username": "agent1",
  "password": "courier123"
}
`

**Response (200):**
`json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 28800,
  "agent": {
    "id": "uuid",
    "name": "Agent 1",
    "shift_start": "08:00:00",
    "shift_end": "17:00:00",
    "status": "idle"
  }
}
`

**Error (401):**
`json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid username or password"
  }
}
`

#### GET /auth/me

Get the currently authenticated agent's details.

**Headers:** Authorization: Bearer <token>

**Response (200):**
`json
{
  "id": "uuid",
  "name": "Agent 1",
  "shift_start": "08:00:00",
  "shift_end": "17:00:00",
  "status": "idle"
}
`

---

### 3.2 Requests

#### POST /requests

Create a new pickup request. **Public endpoint** (no auth required).

**Request:**
`json
{
  "customer_name": "John Doe",
  "phone": "+1234567890",
  "address": "123 Main St, City",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "window_start": "2026-10-10T14:00:00Z",
  "window_end": "2026-10-10T16:00:00Z",
  "priority": "normal"
}
`

**Validation Rules:**
- window_end must be after window_start
- window_start must be in the future (at least 1 minute from now)
- window_start and window_end must overlap at least one agent's shift
- latitude must be between -90 and 90
- longitude must be between -180 and 180
- priority must be one of: urgent, normal, low

**Response (201):**
`json
{
  "id": "uuid",
  "customer_name": "John Doe",
  "phone": "+1234567890",
  "address": "123 Main St, City",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "window_start": "2026-10-10T14:00:00Z",
  "window_end": "2026-10-10T16:00:00Z",
  "priority": "normal",
  "status": "Pending",
  "assigned_agent_id": null,
  "scheduled_time": null,
  "unassigned_reason": null,
  "created_at": "2026-10-10T10:00:00Z"
}
`

**Error (400) - Example validation failures:**
`json
{
  "error": {
    "code": "INVALID_WINDOW",
    "message": "window_end must be after window_start",
    "field": "window_end"
  }
}
`
`json
{
  "error": {
    "code": "WINDOW_IN_PAST",
    "message": "window_start must be in the future",
    "field": "window_start"
  }
}
`
`json
{
  "error": {
    "code": "NO_AGENT_AVAILABLE",
    "message": "No agent is available during the requested time window",
    "field": "window_start"
  }
}
`

#### GET /requests

List pickup requests with optional filters. **Public endpoint.**

**Query Parameters:**
- status (optional): Filter by status
- gent_id (optional): Filter by assigned agent
- date (optional): Filter by date (YYYY-MM-DD)

**Response (200):**
`json
[
  {
    "id": "uuid",
    "customer_name": "John Doe",
    "status": "Pending",
    "assigned_agent_id": "uuid",
    "scheduled_time": "2026-10-10T14:30:00Z",
    "priority": "normal"
  }
]
`

#### GET /requests/{id}

Get request detail with full status history. **Public endpoint** (for customer tracking).

**Response (200):**
`json
{
  "id": "uuid",
  "customer_name": "John Doe",
  "phone": "+1234567890",
  "address": "123 Main St, City",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "window_start": "2026-10-10T14:00:00Z",
  "window_end": "2026-10-10T16:00:00Z",
  "priority": "normal",
  "status": "Scheduled",
  "assigned_agent_id": "uuid",
  "scheduled_time": "2026-10-10T14:30:00Z",
  "unassigned_reason": null,
  "created_at": "2026-10-10T10:00:00Z",
  "status_history": [
    {
      "status": "Pending",
      "timestamp": "2026-10-10T10:00:00Z"
    },
    {
      "status": "Scheduled",
      "timestamp": "2026-10-10T10:00:05Z"
    }
  ]
}
`

#### PATCH /requests/{id}/cancel

Cancel a pickup request. **Public endpoint.**

**Behavior:**
- Only requests in status Pending, Scheduled, or Unassigned can be cancelled
- Sets status to Cancelled
- Frees the agent's slot
- Triggers automatic re-scheduling for affected agent

**Response (200):**
`json
{
  "id": "uuid",
  "status": "Cancelled",
  "message": "Request cancelled successfully"
}
`

**Error (409):**
`json
{
  "error": {
    "code": "INVALID_TRANSITION",
    "message": "Cannot cancel a request that is already En route, Picked up, or Delivered"
  }
}
`

#### PATCH /requests/{id}/status

Update request status (agent action). **Requires agent auth.**

**Headers:** Authorization: Bearer <token>

**Request:**
`json
{
  "status": "En route"
}
`

**Allowed Transitions:**
| Current Status | Allowed Next Status |
|---------------|-------------------|
| Scheduled | En route, Cancelled |
| En route | Picked up, Cancelled |
| Picked up | Delivered to hub |
| Pending | Cancelled |
| Unassigned | Cancelled, Scheduled |

**Validation:**
- The authenticated agent must be the assigned agent (for En route, Picked up, Delivered to hub)
- Transition must be in the allowed list above

**Response (200):**
`json
{
  "id": "uuid",
  "status": "En route",
  "status_history": [
    {"status": "Pending", "timestamp": "..."},
    {"status": "Scheduled", "timestamp": "..."},
    {"status": "En route", "timestamp": "..."}
  ]
}
`

**Error (403):**
`json
{
  "error": {
    "code": "NOT_ASSIGNED",
    "message": "You are not assigned to this request"
  }
}
`

**Error (409):**
`json
{
  "error": {
    "code": "INVALID_TRANSITION",
    "message": "Cannot transition from Picked up to Scheduled"
  }
}
`

---

### 3.3 Agents

#### GET /agents

List all agents and their current status. **Public endpoint.**

**Response (200):**
`json
[
  {
    "id": "uuid",
    "name": "Agent 1",
    "shift_start": "08:00:00",
    "shift_end": "17:00:00",
    "status": "idle",
    "current_location": {
      "latitude": 12.9716,
      "longitude": 77.5946
    }
  }
]
`

#### GET /agents/{id}/schedule

Get ordered pickups for one agent. **Requires agent auth** (can only view own schedule).

**Headers:** Authorization: Bearer <token>

**Response (200):**
`json
{
  "agent": {
    "id": "uuid",
    "name": "Agent 1"
  },
  "schedule": [
    {
      "request_id": "uuid",
      "customer_name": "John Doe",
      "address": "123 Main St",
      "latitude": 12.9716,
      "longitude": 77.5946,
      "scheduled_time": "2026-10-10T14:30:00Z",
      "window_start": "2026-10-10T16:00:00Z",
      "status": "Scheduled",
      "estimated_travel_time_seconds": 600
    }
  ],
  "total_travel_time_seconds": 3600,
  "estimated_times": false
}
`

**Note:** estimated_times is true when OSRM was unavailable and haversine fallback was used.

---

### 3.4 Scheduler

#### POST /schedule/run

Manually trigger the scheduler on all unstarted requests. **Requires agent auth.**

**Headers:** Authorization: Bearer <token>

**Behavior:**
- Runs the scheduling algorithm on all requests with status Pending or Unassigned
- Only affects requests that are not En route or Picked up
- Returns summary of changes

**Response (200):**
`json
{
  "scheduled": 5,
  "unassigned": 1,
  "details": [
    {
      "request_id": "uuid",
      "action": "scheduled",
      "assigned_agent_id": "uuid",
      "scheduled_time": "2026-10-10T14:30:00Z"
    },
    {
      "request_id": "uuid",
      "action": "unassigned",
      "reason": "No agent can reach this pickup within the requested window",
      "suggested_slot": {
        "agent_id": "uuid",
        "time": "2026-10-11T09:00:00Z"
      }
    }
  ]
}
`

---

### 3.5 Demo

#### POST /demo/seed

Load demo agents and overlapping pickups. **Requires agent auth.**

**Headers:** Authorization: Bearer <token>

**Behavior:**
- Creates 3 agents with usernames agent1, agent2, agent3 (password: courier123)
- Creates 6 pickup requests with overlapping windows
- Clears existing demo data first (optional query param ?reset=true)

**Response (200):**
`json
{
  "agents_created": 3,
  "requests_created": 6
}
`

#### POST /demo/urgent

Create an urgent pickup for the live demo. **Requires agent auth.**

**Headers:** Authorization: Bearer <token>

**Behavior:**
- Creates an urgent pickup request at a random location near existing pickups
- Triggers urgent insertion logic
- Returns the created request and schedule changes

**Response (200):**
`json
{
  "request": { ... },
  "affected_agents": ["uuid"],
  "bumped_requests": []
}
`

---

## 4. Scheduler Engine

### 4.1 Overview

The scheduler is the core intelligence of the system. It assigns pending pickup requests to agents, orders each agent's route, and handles urgent insertions.

### 4.2 Priority Queue

Pending requests are stored in a priority queue (Python heapq) sorted by:

`python
heapq_tuple = (-priority_tier, window_end, extra_travel_time, created_at)
`

Where:
- priority_tier: 0=urgent, 1=normal, 2=low (negated for max-heap behavior)
- window_end: datetime (earlier deadline = higher priority)
- extra_travel_time: seconds (from OSRM or haversine fallback)
- created_at: datetime (tiebreaker — earlier requests first)

### 4.3 Priority Aging

Priority tiers are promoted as deadlines approach:

| Time Until Deadline | Promotion |
|---------------------|-----------|
| < 24 hours | low → normal |
| < 2 hours | normal → urgent |

This ensures no request starves indefinitely.

### 4.4 Assignment Algorithm

`
For each pending request in priority queue order:
    1. Get all agents
    2. Filter agents who can reach the pickup, collect, and deliver within the window
       (using OSRM travel times + 5-minute service time)
    3. If no agents available:
       - Mark request as Unassigned with reason
       - Suggest next free slot (gap analysis in next 48 hours)
    4. Apply near-route rule:
       - For each agent, check if any active pickup is within 2 km of new request
         using: SELECT * FROM pickup_requests 
               WHERE assigned_agent_id = :agent_id 
               AND status IN ('Scheduled', 'En route', 'Picked up')
               AND ST_DWithin(location, :new_location, 2000)
       - If near-route candidates exist, calculate insertion cost for each
    5. If near-route insertion is cheaper than assigning to a different agent:
       - Assign to that agent
       - Insert at cheapest position in route
    6. Otherwise:
       - Assign to agent with least extra travel time
    7. Update request: status = Scheduled, assigned_agent_id = agent, scheduled_time = calculated
    8. Insert status_history row
`

### 4.5 Agent Route Ordering

Each agent's pickups are ordered by:
1. Window time (earlier first)
2. Nearest next stop (minimize travel between consecutive pickups)

### 4.6 Urgent Insertion

When an urgent request arrives after scheduling:

`
1. For each agent:
   a. Try inserting the urgent request at every position in their current route
   b. Calculate added travel time for each position (OSRM/haversine)
   c. Record the (agent, position) pair with least added travel time
2. Select the best (agent, position) pair
3. Insert the urgent request
4. If insertion breaks another pickup's window:
   - Push the lowest-priority affected pickup back to pending queue
   - Re-run assignment for that pickup
5. Urgent requests are never silently dropped
`

### 4.7 OSRM Integration

`python
async def get_travel_time_matrix(locations: list[dict]) -> dict:
    """
    Get travel time matrix from OSRM.
    Falls back to haversine * 1.3 at 30 km/h on failure.
    """
    try:
        response = await httpx.AsyncClient(timeout=3.0).post(
            f"{OSRM_URL}/table/v1/driving/",
            json={"coordinates": locations}  # [[lon, lat], ...]
        )
        response.raise_for_status()
        return {"matrix": response.json()["durations"], "estimated": False}
    except (httpx.TimeoutException, httpx.HTTPError):
        logger.warning("OSRM unavailable, using haversine fallback")
        matrix = haversine_matrix(locations, road_factor=1.3, speed_kmh=30)
        return {"matrix": matrix, "estimated": True}
`

### 4.8 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| OSRM_URL | https://router.project-osrm.org | OSRM server URL |
| OSRM_TIMEOUT | 3.0 | Timeout in seconds |
| HUB_LATITUDE | 12.9716 | Hub location |
| HUB_LONGITUDE | 77.5946 | Hub location |
| SERVICE_TIME_MINUTES | 5 | Fixed service time per pickup |
| NEAR_ROUTE_RADIUS_METERS | 2000 | Near-route rule radius |
| FALLBACK_ROAD_FACTOR | 1.3 | Haversine road factor |
| FALLBACK_SPEED_KMH | 30 | Fallback average speed |
| JWT_SECRET | (required) | JWT signing secret |
| JWT_EXPIRY_HOURS | 8 | Token expiry |

---

## 5. Authentication

### 5.1 JWT Token Flow

`
Agent → POST /auth/login → FastAPI validates credentials
                            ↓
                    bcrypt.verify(password, hash)
                            ↓
                    JWT.create({
                        sub: agent_id,
                        name: agent_name,
                        exp: now + 8h
                    })
                            ↓
                    Return token to client
`

### 5.2 Protected Endpoints

| Endpoint | Auth Required |
|----------|--------------|
| POST /auth/login | No |
| GET /auth/me | Yes |
| POST /requests | No |
| GET /requests | No |
| GET /requests/{id} | No |
| PATCH /requests/{id}/cancel | No |
| PATCH /requests/{id}/status | Yes |
| GET /agents | No |
| GET /agents/{id}/schedule | Yes |
| POST /schedule/run | Yes |
| POST /demo/seed | Yes |
| POST /demo/urgent | Yes |

---

## 6. Error Handling

### 6.1 Error Response Format

All errors follow this structure:

`json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human-readable description of what went wrong",
    "field": "field_name_if_applicable",
    "details": {}
  }
}
`

### 6.2 HTTP Status Codes

| Code | Usage |
|------|-------|
| 400 | Validation error (invalid input) |
| 401 | Authentication required / invalid credentials |
| 403 | Authenticated but not authorized |
| 404 | Resource not found |
| 409 | Conflict (invalid state transition) |
| 500 | Internal server error |

### 6.3 Error Codes

| Code | Message | HTTP |
|------|---------|------|
| INVALID_WINDOW | window_end must be after window_start | 400 |
| WINDOW_IN_PAST | window_start must be in the future | 400 |
| NO_AGENT_AVAILABLE | No agent is available during the requested time window | 400 |
| INVALID_PRIORITY | priority must be one of: urgent, normal, low | 400 |
| INVALID_CREDENTIALS | Invalid username or password | 401 |
| TOKEN_EXPIRED | Authentication token has expired | 401 |
| NOT_ASSIGNED | You are not assigned to this request | 403 |
| INVALID_TRANSITION | Cannot transition from {from} to {to} | 409 |
| REQUEST_NOT_FOUND | Pickup request not found | 404 |

---

## 7. Project Structure

`
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment configuration
│   ├── database.py          # SQLAlchemy engine & session
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── auth.py              # JWT authentication utilities
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # /auth endpoints
│   │   ├── requests.py      # /requests endpoints
│   │   ├── agents.py        # /agents endpoints
│   │   ├── schedule.py      # /schedule endpoints
│   │   └── demo.py          # /demo endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scheduler.py     # Scheduling engine
│   │   ├── osrm.py          # OSRM client with fallback
│   │   └── haversine.py     # Fallback distance calculation
│   └── utils/
│       ├── __init__.py
│       └── validators.py    # Custom validators
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_requests.py
│   ├── test_scheduler.py
│   └── test_osrm.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
`

---

## 8. Seed Data

### 8.1 Demo Agents

| Username | Password | Shift |
|----------|----------|-------|
| agent1 | courier123 | 08:00 - 17:00 |
| agent2 | courier123 | 08:00 - 17:00 |
| agent3 | courier123 | 09:00 - 18:00 |

### 8.2 Demo Pickups

6 pickup requests with overlapping windows, geographically clustered near the hub. Exact coordinates defined in seed script.

---

## 9. Deployment

### 9.1 Docker Compose

`yaml
version: '3.8'
services:
  db:
    image: postgis/postgis:15-3.3
    environment:
      POSTGRES_DB: courier
      POSTGRES_USER: courier
      POSTGRES_PASSWORD: courier
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://courier:courier@db:5432/courier
      JWT_SECRET: 
      OSRM_URL: https://router.project-osrm.org
    ports:
      - "8000:8000"
    depends_on:
      - db

volumes:
  pgdata:
`

---

*End of Backend Specification*
