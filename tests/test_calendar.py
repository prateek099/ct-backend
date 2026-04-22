"""Tests for /api/v1/calendar — content calendar events."""
from datetime import datetime, timedelta


def _body(offset_days: int = 0, **overrides) -> dict:
    when = (datetime(2026, 5, 1, 10, 0) + timedelta(days=offset_days)).isoformat()
    body = {
        "title": "Record episode",
        "event_type": "record",
        "scheduled_for": when,
    }
    body.update(overrides)
    return body


def test_unauth_blocked(client):
    assert client.get("/api/v1/calendar/").status_code == 401


def test_crud_flow(client, auth_headers):
    res = client.post("/api/v1/calendar/", json=_body(), headers=auth_headers)
    assert res.status_code == 201
    created = res.json()
    assert created["event_type"] == "record"

    res = client.patch(
        f"/api/v1/calendar/{created['id']}",
        json={"title": "Record pilot"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Record pilot"
    assert res.json()["event_type"] == "record"

    res = client.delete(
        f"/api/v1/calendar/{created['id']}", headers=auth_headers
    )
    assert res.status_code == 204

    res = client.get("/api/v1/calendar/", headers=auth_headers)
    assert res.json() == []


def test_invalid_event_type_rejected(client, auth_headers):
    res = client.post(
        "/api/v1/calendar/",
        json=_body(event_type="bogus"),
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_date_range_filter(client, auth_headers):
    for i in range(5):
        client.post(
            "/api/v1/calendar/", json=_body(offset_days=i), headers=auth_headers
        )
    res = client.get(
        "/api/v1/calendar/",
        params={
            "from": datetime(2026, 5, 2).isoformat(),
            "to": datetime(2026, 5, 3, 23, 59).isoformat(),
        },
        headers=auth_headers,
    )
    assert len(res.json()) == 2


def test_cross_user_404(client, auth_headers, admin_auth_headers):
    created = client.post(
        "/api/v1/calendar/", json=_body(), headers=auth_headers
    ).json()
    res = client.get(
        f"/api/v1/calendar/{created['id']}", headers=admin_auth_headers
    )
    assert res.status_code == 404
    res = client.patch(
        f"/api/v1/calendar/{created['id']}",
        json={"title": "x"},
        headers=admin_auth_headers,
    )
    assert res.status_code == 404


def test_list_is_user_scoped(client, auth_headers, admin_auth_headers):
    client.post("/api/v1/calendar/", json=_body(), headers=auth_headers)
    res = client.get("/api/v1/calendar/", headers=admin_auth_headers)
    assert res.json() == []
