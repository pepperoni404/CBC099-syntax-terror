# Smart Courier Pickup Scheduling System

## Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

### Run Everything

Just clone the repo and run Docker
That's it. The application will be available at:

| Service | URL |
|---------|-----|
| http://localhost:3000 |
### Default Login Credentials

| Username | Password |
|----------|----------|
| agent1 | courier123 |
| agent2 | courier123 |
| agent3 | courier123 |

### Seed Demo Data

The database is automatically seeded with demo agents and pickup requests on first run.

To re-seed (reset all data):
`ash
docker compose down -v
docker compose up --build
`

---

## Development Setup (without Docker)

### Backend

`ash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
`

Start PostgreSQL with PostGIS locally, then:

`ash
export DATABASE_URL=postgresql://courier:courier@localhost:5432/courier
export JWT_SECRET=dev-secret-key
uvicorn app.main:app --port 8000 --reload
`

### Frontend

`ash
cd frontend
npm install
npm run dev
`

The frontend will be available at http://localhost:3000 and proxy API requests to localhost:8000.

---

## Project Structure

`
CBC 2.0/
├── docker-compose.yml       ← One command starts everything
├── README.md                ← This file
├── specs/
│   ├── backend-spec.md
│   ├── frontend-spec.md
│   └── integration-guide.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth.py
│   │   ├── routers/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── entrypoint.sh        ← Runs migrations + seed on startup
└── frontend/
    ├── src/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── Dockerfile
`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/login | Agent login |
| GET | /auth/me | Current agent info |
| POST | /requests | Create pickup request |
| GET | /requests | List requests |
| GET | /requests/{id} | Request detail + history |
| PATCH | /requests/{id}/cancel | Cancel request |
| PATCH | /requests/{id}/status | Update status |
| GET | /agents | List agents |
| GET | /agents/{id}/schedule | Agent schedule |
| POST | /schedule/run | Run scheduler |
| POST | /demo/seed | Seed demo data |
| POST | /demo/urgent | Create urgent demo pickup |

Full API documentation is available at http://localhost:8000/docs when the backend is running.

---

## How It Works

1. **Customer** submits a pickup request with a time window
2. **Backend** validates the request and saves it to PostgreSQL
3. **Scheduler** assigns the request to the best available agent using OSRM travel times
4. **Dispatcher** sees the assignment on the map and calendar
5. **Agent** receives the pickup on their dashboard and updates status as they progress
6. **Customer** tracks their pickup in real-time

---

## Stopping the Application

`ash
docker compose down
`

To remove all data (including the database):
`ash
docker compose down -v
`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 3000 already in use | Change 3000:3000 to 3001:3000 in docker-compose.yml |
| Port 8000 already in use | Change 8000:8000 to 8001:8000 in docker-compose.yml |
| Database connection failed | Make sure port 5432 is not in use by another PostgreSQL instance |
| Frontend can't reach backend | Check that VITE_API_URL matches your backend URL |

---

## License

MIT
