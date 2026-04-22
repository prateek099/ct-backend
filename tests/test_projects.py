"""Tests for /api/v1/projects/* — CRUD, auth, ownership."""


def test_list_projects_requires_auth(client):
    res = client.get("/api/v1/projects/")
    assert res.status_code == 401


def test_create_and_get_project(client, auth_headers):
    res = client.post(
        "/api/v1/projects/",
        json={
            "title": "My first idea",
            "idea_json": {"topic": "morning routines", "angle": "science-backed"},
        },
        headers=auth_headers,
    )
    assert res.status_code == 201
    proj = res.json()
    assert proj["title"] == "My first idea"
    assert proj["status"] == "draft"
    assert proj["idea_json"]["topic"] == "morning routines"
    assert proj["id"] > 0

    res = client.get(f"/api/v1/projects/{proj['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["title"] == "My first idea"


def test_list_projects_returns_only_own(client, auth_headers):
    client.post("/api/v1/projects/", json={"title": "A"}, headers=auth_headers)
    client.post("/api/v1/projects/", json={"title": "B"}, headers=auth_headers)
    res = client.get("/api/v1/projects/", headers=auth_headers)
    assert res.status_code == 200
    titles = [p["title"] for p in res.json()]
    assert set(titles) == {"A", "B"}


def test_patch_project_partial_update(client, auth_headers):
    res = client.post(
        "/api/v1/projects/",
        json={"title": "Draft", "idea_json": {"topic": "x"}},
        headers=auth_headers,
    )
    pid = res.json()["id"]

    # Prateek: patch only the script blob — title and idea_json must stay intact.
    res = client.patch(
        f"/api/v1/projects/{pid}",
        json={"script_json": {"body": "hello"}},
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "Draft"
    assert body["idea_json"] == {"topic": "x"}
    assert body["script_json"] == {"body": "hello"}


def test_patch_status_to_published(client, auth_headers):
    res = client.post("/api/v1/projects/", json={"title": "Ship"}, headers=auth_headers)
    pid = res.json()["id"]

    res = client.patch(
        f"/api/v1/projects/{pid}", json={"status": "published"}, headers=auth_headers
    )
    assert res.status_code == 200
    assert res.json()["status"] == "published"


def test_patch_invalid_status_rejected(client, auth_headers):
    res = client.post("/api/v1/projects/", json={"title": "X"}, headers=auth_headers)
    pid = res.json()["id"]

    res = client.patch(
        f"/api/v1/projects/{pid}", json={"status": "nonsense"}, headers=auth_headers
    )
    assert res.status_code == 422


def test_delete_project(client, auth_headers):
    res = client.post("/api/v1/projects/", json={"title": "Goner"}, headers=auth_headers)
    pid = res.json()["id"]

    res = client.delete(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert res.status_code == 204

    res = client.get(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert res.status_code == 404


def test_other_users_project_returns_404(client, auth_headers):
    """Ownership: user A cannot see user B's project — 404, not 403, to avoid leaking existence."""
    # Prateek: create project as user A.
    res = client.post("/api/v1/projects/", json={"title": "A's"}, headers=auth_headers)
    pid = res.json()["id"]

    # Register + login user B directly.
    client.post(
        "/api/v1/auth/register",
        json={"name": "B", "email": "b@example.com", "password": "bpass123"},
    )
    res = client.post(
        "/api/v1/auth/login", json={"email": "b@example.com", "password": "bpass123"}
    )
    b_token = res.json()["access_token"]
    b_headers = {"Authorization": f"Bearer {b_token}"}

    res = client.get(f"/api/v1/projects/{pid}", headers=b_headers)
    assert res.status_code == 404

    res = client.patch(
        f"/api/v1/projects/{pid}", json={"title": "hijack"}, headers=b_headers
    )
    assert res.status_code == 404

    res = client.delete(f"/api/v1/projects/{pid}", headers=b_headers)
    assert res.status_code == 404

    # Prateek: A's list must not contain B's projects (B has none, but check scoping).
    res = client.get("/api/v1/projects/", headers=b_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_filters_by_status(client, auth_headers):
    client.post(
        "/api/v1/projects/", json={"title": "Draft1"}, headers=auth_headers
    )
    res = client.post(
        "/api/v1/projects/",
        json={"title": "Pub1", "status": "published"},
        headers=auth_headers,
    )
    assert res.status_code == 201

    res = client.get("/api/v1/projects/?status=published", headers=auth_headers)
    assert res.status_code == 200
    titles = [p["title"] for p in res.json()]
    assert titles == ["Pub1"]
