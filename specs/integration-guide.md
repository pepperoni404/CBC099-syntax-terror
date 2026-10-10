# Integration Guide: Smart Courier Pickup Scheduling System

**Date:** 2026-10-10
**Status:** Draft for review

---

## Purpose

This document is the **contract** between the frontend and backend implementations. Both implementation agents MUST follow this guide exactly. Any deviation will cause integration failures.

---

## 1. Repository Structure

Both implementations live in the **same GitHub repository**:

`
CBC 2.0/
├── specs/
│   ├── backend-spec.md
│   ├── frontend-spec.md
│   └── integration-guide.md    ← this file
├── backend/                    ← backend agent works here
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/                   ← frontend agent works here
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
└── README.md
`

---

## 2. API Contract

### 2.1 Base URL

| Environment | Backend URL | Frontend URL |
|-------------|-------------|--------------|
| Local development | http://localhost:8000 | http://localhost:3000 |
| Production | (TBD) | (TBD) |

### 2.2 Request/Response Format

- **Content-Type:** pplication/json for all requests and responses
- **Date/Time format:** ISO 8601 with timezone (e.g., 2026-10-10T14:00:00Z)
- **Coordinate order:** Always { "latitude": X, "longitude": Y } (lat first, then lon)
- **OSRM coordinate order:** Internally, OSRM expects [longitude, latitude] (lon first, then lat). The backend handles this conversion.

### 2.3 Error Response Format

ALL errors MUST follow this exact structure:

`json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human-readable description of what went wrong",
    "field": "field_name_if_applicable"
  }
}
`

**Important:** The ield property is optional and only included for validation errors.

### 2.4 Standard Error Codes

| Code | HTTP Status | Message | When |
|------|-------------|---------|------|
| INVALID_WINDOW | 400 | window_end must be after window_start | window_end <= window_start |
| WINDOW_IN_PAST | 400 | window_start must be in the future | window_start < now |
| NO_AGENT_AVAILABLE | 400 | No agent is available during the requested time window | No agent shift overlaps window |
| INVALID_PRIORITY | 400 | priority must be one of: urgent, normal, low | Invalid priority value |
| INVALID_COORDINATES | 400 | latitude must be between -90 and 90 | Invalid latitude |
| INVALID_CREDENTIALS | 401 | Invalid username or password | Wrong username or password |
| TOKEN_EXPIRED | 401 | Authentication token has expired | JWT expired |
| NOT_AUTHENTICATED | 401 | Authentication required | No token provided |
| NOT_ASSIGNED | 403 | You are not assigned to this request | Agent tries to update request not assigned to them |
| INVALID_TRANSITION | 409 | Cannot transition from {from} to {to} | Invalid status change |
| REQUEST_NOT_FOUND | 404 | Pickup request not found | Request ID doesn't exist |
| AGENT_NOT_FOUND | 404 | Agent not found | Agent ID doesn't exist |
| INTERNAL_ERROR | 500 | Internal server error | Unexpected error |

### 2.5 Endpoint Specifications

#### POST /auth/login

**Request:**
`json
{
  "username": "string",
  "password": "string"
}
`

**Response (200):**
`json
{
  "access_token": "string (JWT)",
  "token_type": "bearer",
  "expires_in": 28800,
  "agent": {
    "id": "uuid",
    "name": "string",
    "shift_start": "HH:MM:SS",
    "shift_end": "HH:MM:SS",
    "status": "string"
  }
}
`

**Errors:** 401 INVALID_CREDENTIALS

---

#### GET /auth/me

**Headers:** Authorization: Bearer <token>

**Response (200):**
`json
{
  "id": "uuid",
  "name": "string",
  "shift_start": "HH:MM:SS",
  "shift_end": "HH:MM:SS",
  "status": "string"
}
`

**Errors:** 401 NOT_AUTHENTICATED, 401 TOKEN_EXPIRED

---

#### POST /requests

**Headers:** None (public endpoint)

**Request:**
`json
{
  "customer_name": "string (max 100)",
  "phone": "string (max 20)",
  "address": "string (max 255)",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "window_start": "2026-10-10T14:00:00Z",
  "window_end": "2026-10-10T16:00:00Z",
  "priority": "normal"
}
`

**Response (201):**
`json
{
  "id": "uuid",
  "customer_name": "string",
  "phone": "string",
  "address": "string",
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

**Errors:** 400 INVALID_WINDOW, 400 WINDOW_IN_PAST, 400 NO_AGENT_AVAILABLE, 400 INVALID_PRIORITY, 400 INVALID_COORDINATES

---

#### GET /requests

**Headers:** None (public endpoint)

**Query Parameters:**
- status (optional): string — filter by status
- gent_id (optional): uuid — filter by assigned agent
- date (optional): YYYY-MM-DD — filter by date

**Response (200):**
`json
[
  {
    "id": "uuid",
    "customer_name": "string",
    "status": "string",
    "assigned_agent_id": "uuid or null",
    "scheduled_time": "ISO8601 or null",
    "priority": "string"
  }
]
`

---

#### GET /requests/{id}

**Headers:** None (public endpoint)

**Response (200):**
`json
{
  "id": "uuid",
  "customer_name": "string",
  "phone": "string",
  "address": "string",
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

**Errors:** 404 REQUEST_NOT_FOUND

---

#### PATCH /requests/{id}/cancel

**Headers:** None (public endpoint)

**Response (200):**
`json
{
  "id": "uuid",
  "status": "Cancelled",
  "message": "Request cancelled successfully"
}
`

**Errors:** 404 REQUEST_NOT_FOUND, 409 INVALID_TRANSITION (if En route, Picked up, or Delivered)

---

#### PATCH /requests/{id}/status

**Headers:** Authorization: Bearer <token>

**Request:**
`json
{
  "status": "En route"
}
`

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

**Errors:** 401 NOT_AUTHENTICATED, 403 NOT_ASSIGNED, 404 REQUEST_NOT_FOUND, 409 INVALID_TRANSITION

---

#### GET /agents

**Headers:** None (public endpoint)

**Response (200):**
`json
[
  {
    "id": "uuid",
    "name": "string",
    "shift_start": "HH:MM:SS",
    "shift_end": "HH:MM:SS",
    "status": "string",
    "current_location": {
      "latitude": 12.9716,
      "longitude": 77.5946
    }
  }
]
`

---

#### GET /agents/{id}/schedule

**Headers:** Authorization: Bearer <token>

**Response (200):**
`json
{
  "agent": {
    "id": "uuid",
    "name": "string"
  },
  "schedule": [
    {
      "request_id": "uuid",
      "customer_name": "string",
      "address": "string",
      "latitude": 12.9716,
      "longitude": 77.5946,
      "scheduled_time": "2026-10-10T14:30:00Z",
      "window_end": "2026-10-10T16:00:00Z",
      "status": "Scheduled",
      "estimated_travel_time_seconds": 600
    }
  ],
  "total_travel_time_seconds": 3600,
  "estimated_times": false
}
`

**Errors:** 401 NOT_AUTHENTICATED, 403 NOT_ASSIGNED (can only view own schedule), 404 AGENT_NOT_FOUND

---

#### POST /schedule/run

**Headers:** Authorization: Bearer <token>

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

**Errors:** 401 NOT_AUTHENTICATED

---

#### POST /demo/seed

**Headers:** Authorization: Bearer <token>

**Response (200):**
`json
{
  "agents_created": 3,
  "requests_created": 6
}
`

**Errors:** 401 NOT_AUTHENTICATED

---

#### POST /demo/urgent

**Headers:** Authorization: Bearer <token>

**Response (200):**
`json
{
  "request": {
    "id": "uuid",
    "customer_name": "Urgent Customer",
    "status": "Scheduled",
    "priority": "urgent"
  },
  "affected_agents": ["uuid"],
  "bumped_requests": []
}
`

**Errors:** 401 NOT_AUTHENTICATED

---

## 3. Environment Variables

### Backend Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DATABASE_URL | Yes | — | PostgreSQL connection string |
| JWT_SECRET | Yes | — | Secret for signing JWT tokens |
| JWT_EXPIRY_HOURS | No | 8 | Token expiry in hours |
| OSRM_URL | No | https://router.project-osrm.org | OSRM server URL |
| OSRM_TIMEOUT | No | 3.0 | OSRM timeout in seconds |
| HUB_LATITUDE | No | 12.9716 | Hub location latitude |
| HUB_LONGITUDE | No | 77.5946 | Hub location longitude |
| SERVICE_TIME_MINUTES | No | 5 | Service time per pickup in minutes |
| NEAR_ROUTE_RADIUS_METERS | No | 2000 | Near-route rule radius |
| FALLBACK_ROAD_FACTOR | No | 1.3 | Haversine road factor |
| FALLBACK_SPEED_KMH | No | 30 | Fallback average speed |
| ALLOWED_ORIGINS | No | http://localhost:3000 | CORS allowed origins (comma-separated) |

### Frontend Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| VITE_API_URL | No | http://localhost:8000 | Backend API base URL |

---

## 4. CORS Configuration

The backend MUST allow requests from the frontend origin.

**Development:**
- Backend allows: http://localhost:3000
- Configured via ALLOWED_ORIGINS=http://localhost:3000

**Production:**
- Backend allows: (production frontend URL)
- Configured via ALLOWED_ORIGINS=https://yourdomain.com

---

## 5. Git Workflow

### 5.1 Branch Strategy

`
main (production-ready)
├── backend-dev    ← backend agent works here
└── frontend-dev   ← frontend agent works here
`

### 5.2 Pull Request Process

1. Agent completes their implementation
2. Agent runs the compatibility checklist (see Section 6)
3. Agent opens a PR to main
4. You review and merge
5. Integration test on main

### 5.3 Commit Message Convention

`
<type>: <description>

Types:
- feat: new feature
- fix: bug fix
- docs: documentation changes
- chore: build/config changes
`

---

## 6. Compatibility Checklist

### Backend Checklist (before pushing)

- [ ] All endpoints return the exact JSON structure specified in Section 2.5
- [ ] All error responses follow the format in Section 2.3
- [ ] Error codes match Section 2.4 exactly
- [ ] CORS allows the frontend origin
- [ ] JWT tokens are created with the sub claim set to agent ID
- [ ] JWT tokens expire after 8 hours
- [ ] All timestamps are in ISO 8601 format with timezone
- [ ] Coordinates are always { latitude, longitude } (lat first)
- [ ] Database schema matches the backend spec exactly
- [ ] Seed data creates agents with usernames: agent1, agent2, agent3 (password: courier123)

### Frontend Checklist (before pushing)

- [ ] API client uses the exact endpoint paths from Section 2.5
- [ ] All error messages are displayed to the user (not just logged)
- [ ] Error codes from Section 2.4 are handled appropriately
- [ ] JWT token is stored in localStorage under key gent_token
- [ ] Authorization header is sent as Bearer <token>
- [ ] Polling interval is exactly 30 seconds (30000ms)
- [ ] All timestamps are displayed in local timezone
- [ ] Coordinates are always sent as { latitude, longitude } (lat first)
- [ ] Map uses OpenStreetMap tiles
- [ ] All routes match the frontend spec exactly

---

## 7. Integration Testing

After merging both PRs to main, run these tests:

### 7.1 Backend Unit Tests
`ash
cd backend
python -m pytest tests/ -v
`

### 7.2 Frontend Build
`ash
cd frontend
npm install
npm run build
`

### 7.3 End-to-End Integration Test

1. Start PostgreSQL with PostGIS:
   `ash
   docker run -d --name db -p 5432:5432 -e POSTGRES_DB=courier -e POSTGRES_USER=courier -e POSTGRES_PASSWORD=courier postgis/postgis:15-3.3
   `

2. Start backend:
   `ash
   cd backend
   pip install -r requirements.txt
   export DATABASE_URL=postgresql://courier:courier@localhost:5432/courier
   export JWT_SECRET=test-secret
   uvicorn app.main:app --port 8000
   `

3. Start frontend:
   `ash
   cd frontend
   npm install
   npm run dev
   `

4. Test these flows:
   - [ ] Customer submits a pickup request → appears in dispatcher
   - [ ] Agent logs in → sees their schedule
   - [ ] Agent updates status → customer tracking page shows update (within 30s)
   - [ ] Customer cancels request → slot freed, dispatcher sees update
   - [ ] Urgent pickup → schedule rearranges
   - [ ] Invalid window → clear error message shown
   - [ ] OSRM down → "estimated times" badge appears in dispatcher

---

## 8. Common Pitfalls

| Pitfall | Prevention |
|---------|-----------|
| Coordinate order mismatch | Always use { latitude, longitude } in API. OSRM uses [lon, lat] internally — backend handles conversion |
| Timestamp format mismatch | Always use ISO 8601 with timezone (2026-10-10T14:00:00Z) |
| Error format mismatch | Always use { error: { code, message, field } } |
| CORS failures | Backend must allow http://localhost:3000 in development |
| JWT token not sent | Frontend must include Authorization: Bearer <token> header |
| Polling not working | Check that usePolling hook is enabled on correct pages |
| Map not loading | Check that Leaflet CSS is imported and tiles are accessible |

---

## 9. Reproducibility Requirements

### 9.1 What Already Exists (do not modify)

The following files are already in the repository and are shared infrastructure:

```
CBC 2.0/
├── docker-compose.yml       ← Root orchestration (DO NOT MODIFY)
├── README.md                ← Setup instructions (DO NOT MODIFY)
└── specs/                   ← All specification files (DO NOT MODIFY)
```

### 9.2 What the Backend Agent Must Create

```
backend/
├── Dockerfile
├── entrypoint.sh
├── requirements.txt
├── alembic.ini
└── alembic/
    ├── env.py
    └── versions/
        └── 0001_initial_schema.py
```

#### Backend Dockerfile Requirements

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
```

#### Backend entrypoint.sh Requirements

The entrypoint MUST:
1. Wait for the database to be ready (connect to `db:5432`)
2. Run Alembic migrations (`alembic upgrade head`)
3. Seed demo data (idempotent — safe to run multiple times)
4. Start uvicorn on `0.0.0.0:8000`

```bash
#!/bin/bash
set -e

# Wait for database
until python -c "import socket; s=socket.socket(); s.settimeout(1); exit(0 if s.connect_ex(('db', 5432)) == 0 else 1)" 2>/dev/null; do
  sleep 1
done

# Run migrations
alembic upgrade head

# Seed demo data (idempotent)
python -c "from app.database import SessionLocal; from app.services.demo import seed_demo_data; db = SessionLocal(); seed_demo_data(db); db.close()"

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Backend requirements.txt Requirements

Must include at minimum:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
geoalchemy2>=0.14.0
pydantic>=2.0.0
pyjwt>=2.8.0
bcrypt>=4.1.0
httpx>=0.25.0
alembic>=1.13.0
python-dotenv>=1.0.0
```

### 9.3 What the Frontend Agent Must Create

```
frontend/
├── Dockerfile
├── nginx.conf
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── index.html
└── src/
```

#### Frontend Dockerfile Requirements

Multi-stage build:
1. **Build stage:** `node:20-alpine`, run `npm ci` and `npm run build`
2. **Production stage:** `nginx:alpine`, copy built assets, copy `nginx.conf`

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Frontend nginx.conf Requirements

Must handle SPA routing (all routes serve `index.html`):

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 9.4 Reproducibility Checklist

Before pushing, verify:

- [ ] `docker compose up --build` starts all 3 services without errors
- [ ] Frontend at `http://localhost:3000` loads and can submit a request
- [ ] Backend at `http://localhost:8000/docs` shows API documentation
- [ ] Database migrations run automatically on first startup
- [ ] Demo seed data loads automatically
- [ ] All 3 services restart automatically if they crash
- [ ] `docker compose down -v && docker compose up --build` works from scratch

---

*End of Integration Guide*
