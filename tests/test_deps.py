"""Tests for the JWT auth dependencies in app/api/deps.py."""


def test_protected_route_rejects_missing_token(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code in (401, 403)


def test_protected_route_rejects_bad_token(client):
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert res.status_code == 401


def test_protected_route_accepts_valid_token(client, auth_headers):
    res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200


def test_me_returns_current_user(client, auth_headers):
    res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "test@example.com"
