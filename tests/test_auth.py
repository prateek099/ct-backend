"""Tests for /api/v1/auth/* endpoints."""


def test_register(client):
    res = client.post("/api/v1/auth/register", json={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "strongpass",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "alice@example.com"
    assert "hashed_password" not in data   # never leak the hash


def test_register_duplicate_email(client):
    payload = {"name": "Alice", "email": "alice@example.com", "password": "pass"}
    client.post("/api/v1/auth/register", json=payload)
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 409


def test_login_success(client, registered_user):
    res = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, registered_user):
    res = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpass",
    })
    assert res.status_code == 401


def test_login_unknown_email(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "pass",
    })
    assert res.status_code == 401


def test_me(client, auth_headers):
    res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "test@example.com"


def test_me_without_token(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_refresh(client, registered_user):
    login_res = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "secret123",
    })
    refresh_token = login_res.json()["refresh_token"]
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
