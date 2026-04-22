"""Tests for /api/v1/ab-tests — title A/B experiments."""


def _mk_project(client, headers, title="P"):
    res = client.post("/api/v1/projects/", json={"title": title}, headers=headers)
    assert res.status_code == 201
    return res.json()["id"]


def _body(project_id: int, **overrides) -> dict:
    body = {
        "project_id": project_id,
        "title_a": "Title A",
        "title_b": "Title B",
    }
    body.update(overrides)
    return body


def test_unauth_blocked(client):
    assert client.get("/api/v1/ab-tests/").status_code == 401


def test_create_requires_owned_project(client, auth_headers, admin_auth_headers):
    # Prateek: project belongs to admin, not to the auth_headers user.
    pid = _mk_project(client, admin_auth_headers, title="admin-owned")
    res = client.post(
        "/api/v1/ab-tests/", json=_body(pid), headers=auth_headers
    )
    assert res.status_code == 404


def test_crud_flow(client, auth_headers):
    pid = _mk_project(client, auth_headers)
    res = client.post(
        "/api/v1/ab-tests/", json=_body(pid), headers=auth_headers
    )
    assert res.status_code == 201
    created = res.json()
    assert created["status"] == "running"
    assert created["winner"] is None

    res = client.patch(
        f"/api/v1/ab-tests/{created['id']}",
        json={"status": "completed", "winner": "a"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "completed"
    assert body["winner"] == "a"

    res = client.delete(
        f"/api/v1/ab-tests/{created['id']}", headers=auth_headers
    )
    assert res.status_code == 204


def test_only_one_running_per_project(client, auth_headers):
    pid = _mk_project(client, auth_headers)
    res = client.post(
        "/api/v1/ab-tests/", json=_body(pid), headers=auth_headers
    )
    assert res.status_code == 201

    # Prateek: second running test for the same project must conflict.
    res = client.post(
        "/api/v1/ab-tests/",
        json=_body(pid, title_a="A2", title_b="B2"),
        headers=auth_headers,
    )
    assert res.status_code == 409


def test_completed_frees_slot_for_new_running(client, auth_headers):
    pid = _mk_project(client, auth_headers)
    first = client.post(
        "/api/v1/ab-tests/", json=_body(pid), headers=auth_headers
    ).json()
    # Prateek: complete the first test so the partial unique index releases.
    client.patch(
        f"/api/v1/ab-tests/{first['id']}",
        json={"status": "completed", "winner": "b"},
        headers=auth_headers,
    )
    res = client.post(
        "/api/v1/ab-tests/",
        json=_body(pid, title_a="New A", title_b="New B"),
        headers=auth_headers,
    )
    assert res.status_code == 201


def test_invalid_winner_rejected(client, auth_headers):
    pid = _mk_project(client, auth_headers)
    created = client.post(
        "/api/v1/ab-tests/", json=_body(pid), headers=auth_headers
    ).json()
    res = client.patch(
        f"/api/v1/ab-tests/{created['id']}",
        json={"winner": "c"},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_list_filters(client, auth_headers):
    p1 = _mk_project(client, auth_headers, title="P1")
    p2 = _mk_project(client, auth_headers, title="P2")
    client.post("/api/v1/ab-tests/", json=_body(p1), headers=auth_headers)
    t2 = client.post(
        "/api/v1/ab-tests/", json=_body(p2), headers=auth_headers
    ).json()
    client.patch(
        f"/api/v1/ab-tests/{t2['id']}",
        json={"status": "cancelled"},
        headers=auth_headers,
    )

    res = client.get(
        f"/api/v1/ab-tests/?project_id={p1}", headers=auth_headers
    )
    assert len(res.json()) == 1

    res = client.get("/api/v1/ab-tests/?status=running", headers=auth_headers)
    assert len(res.json()) == 1
    assert res.json()[0]["project_id"] == p1


def test_cross_user_404(client, auth_headers, admin_auth_headers):
    pid = _mk_project(client, auth_headers)
    created = client.post(
        "/api/v1/ab-tests/", json=_body(pid), headers=auth_headers
    ).json()
    res = client.get(
        f"/api/v1/ab-tests/{created['id']}", headers=admin_auth_headers
    )
    assert res.status_code == 404
    res = client.patch(
        f"/api/v1/ab-tests/{created['id']}",
        json={"notes": "x"},
        headers=admin_auth_headers,
    )
    assert res.status_code == 404
    res = client.delete(
        f"/api/v1/ab-tests/{created['id']}", headers=admin_auth_headers
    )
    assert res.status_code == 404
