"""
Shared pytest fixtures — DB setup, test client, auth helpers.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


# ── Auth helpers ──────────────────────────────────────────────────────────────

@pytest.fixture
def registered_user(client):
    """Register a user and return their data."""
    res = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "secret123",
    })
    assert res.status_code == 201
    return res.json()


@pytest.fixture
def auth_headers(client, registered_user):
    """Return Authorization headers for the registered test user."""
    res = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
