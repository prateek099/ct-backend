"""Tests for /api/v1/users/* endpoints (all protected)."""


def test_list_users_requires_auth(client):
    res = client.get("/api/v1/users/")
    assert res.status_code == 401


def test_create_and_get_user(client, auth_headers):
    res = client.post("/api/v1/users/", json={
        "name": "Bob",
        "email": "bob@example.com",
        "password": "bobpass",
    }, headers=auth_headers)
    assert res.status_code == 201
    user = res.json()
    assert user["name"] == "Bob"
    assert user["is_active"] is True

    res = client.get(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "bob@example.com"


def test_get_user_not_found(client, auth_headers):
    res = client.get("/api/v1/users/999", headers=auth_headers)
    assert res.status_code == 404


def test_list_users(client, auth_headers):
    client.post("/api/v1/users/", json={
        "name": "Carol", "email": "carol@example.com", "password": "pass"
    }, headers=auth_headers)
    res = client.get("/api/v1/users/", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_delete_user(client, auth_headers):
    res = client.post("/api/v1/users/", json={
        "name": "Dave", "email": "dave@example.com", "password": "pass"
    }, headers=auth_headers)
    user_id = res.json()["id"]
    res = client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert res.status_code == 204

    res = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert res.status_code == 404


def test_duplicate_email(client, auth_headers):
    payload = {"name": "Eve", "email": "eve@example.com", "password": "pass"}
    client.post("/api/v1/users/", json=payload, headers=auth_headers)
    res = client.post("/api/v1/users/", json=payload, headers=auth_headers)
    assert res.status_code == 409
