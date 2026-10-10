#!/bin/bash
set -e

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

# Wait for database
until python -c "import socket; s=socket.socket(); s.settimeout(1); exit(0 if s.connect_ex(('db', 5432)) == 0 else 1)" 2>/dev/null; do
  sleep 1
done

# Run migrations
alembic upgrade head

# Seed demo data (idempotent)
python -c "from app.database import SessionLocal; from app.services.demo import seed_demo_data; db = SessionLocal(); seed_demo_data(db); db.close()"

# Start server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
