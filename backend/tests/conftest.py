from datetime import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models import Agent, coords_to_geography
from app.auth import hash_password, create_access_token

import sqlite3
from sqlalchemy import event

# In-memory SQLite engine for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


from shapely import wkt


@event.listens_for(test_engine, "connect")
def on_sqlite_connect(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.create_function("ST_GeogFromText", 1, lambda x: x)

        def as_binary(val):
            if val is None:
                return None
            if isinstance(val, (bytes, bytearray)):
                return bytes(val)
            try:
                s = str(val)
                if "POINT" in s:
                    s = s[s.find("POINT"):]
                return wkt.loads(s).wkb
            except Exception:
                return None

        dbapi_connection.create_function("AsBinary", 1, as_binary)


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def demo_agents(db):
    agents = [
        Agent(
            name="agent1",
            password_hash=hash_password("courier123"),
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            status="idle",
            current_location=coords_to_geography(12.9716, 77.5946),
        ),
        Agent(
            name="agent2",
            password_hash=hash_password("courier123"),
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            status="idle",
            current_location=coords_to_geography(12.9750, 77.5900),
        ),
        Agent(
            name="agent3",
            password_hash=hash_password("courier123"),
            shift_start=time(9, 0),
            shift_end=time(18, 0),
            status="idle",
            current_location=coords_to_geography(12.9680, 77.6000),
        ),
    ]
    for a in agents:
        db.add(a)
    db.commit()
    for a in agents:
        db.refresh(a)
    return agents


@pytest.fixture
def auth_headers(demo_agents):
    agent1 = demo_agents[0]
    token, _ = create_access_token(str(agent1.id), agent1.name)
    return {"Authorization": f"Bearer {token}"}
