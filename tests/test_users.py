import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# In-memory SQLite for tests
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


client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_create_and_get_user():
    # Create
    res = client.post("/api/v1/users/", json={"name": "Alice", "email": "alice@example.com"})
    assert res.status_code == 201
    user = res.json()
    assert user["name"] == "Alice"
    assert user["id"] is not None

    # Get by ID
    res = client.get(f"/api/v1/users/{user['id']}")
    assert res.status_code == 200
    assert res.json()["email"] == "alice@example.com"


def test_get_user_not_found():
    res = client.get("/api/v1/users/999")
    assert res.status_code == 404


def test_list_users():
    client.post("/api/v1/users/", json={"name": "Bob", "email": "bob@example.com"})
    res = client.get("/api/v1/users/")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_delete_user():
    res = client.post("/api/v1/users/", json={"name": "Charlie", "email": "charlie@example.com"})
    user_id = res.json()["id"]
    res = client.delete(f"/api/v1/users/{user_id}")
    assert res.status_code == 204
