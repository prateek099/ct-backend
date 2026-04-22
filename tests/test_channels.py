"""Tests for /api/v1/channels — cached per-user YT channel snapshots."""
from unittest.mock import patch

CHANNEL_PAYLOAD = {
    "channel_id": "UC-test",
    "channel_name": "Test Channel",
    "handle": "@test",
    "description": "A test channel.",
    "subscriber_count": 1000,
    "total_views": 50000,
    "video_count": 42,
    "thumbnail_url": "https://example.com/t.jpg",
    "recent_videos": [{"id": "v1", "title": "Video 1"}],
    "average_duration_seconds": 420,
}


def _patched():
    return patch(
        "app.services.channel_service.fetch_channel_data",
        return_value=CHANNEL_PAYLOAD,
    )


def test_unauth_cannot_list(client):
    res = client.get("/api/v1/channels/")
    assert res.status_code == 401


def test_create_and_list_channel(client, auth_headers):
    with _patched():
        res = client.post(
            "/api/v1/channels/",
            json={"url": "https://youtube.com/@test"},
            headers=auth_headers,
        )
    assert res.status_code == 201
    body = res.json()
    assert body["channel_name"] == "Test Channel"
    assert body["recent_videos"][0]["title"] == "Video 1"

    res = client.get("/api/v1/channels/", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_duplicate_create_updates_in_place(client, auth_headers):
    with _patched():
        r1 = client.post(
            "/api/v1/channels/",
            json={"url": "https://youtube.com/@test"},
            headers=auth_headers,
        )
        r2 = client.post(
            "/api/v1/channels/",
            json={"url": "https://youtube.com/@test"},
            headers=auth_headers,
        )
    assert r1.json()["id"] == r2.json()["id"]

    res = client.get("/api/v1/channels/", headers=auth_headers)
    assert len(res.json()) == 1


def test_refresh_channel(client, auth_headers):
    with _patched():
        created = client.post(
            "/api/v1/channels/",
            json={"url": "https://youtube.com/@test"},
            headers=auth_headers,
        ).json()
    updated_payload = {**CHANNEL_PAYLOAD, "subscriber_count": 9999}
    with patch(
        "app.services.channel_service.fetch_channel_data",
        return_value=updated_payload,
    ):
        res = client.post(
            f"/api/v1/channels/{created['id']}/refresh", headers=auth_headers
        )
    assert res.status_code == 200
    assert res.json()["subscriber_count"] == 9999


def test_delete_channel(client, auth_headers):
    with _patched():
        created = client.post(
            "/api/v1/channels/",
            json={"url": "https://youtube.com/@test"},
            headers=auth_headers,
        ).json()
    res = client.delete(f"/api/v1/channels/{created['id']}", headers=auth_headers)
    assert res.status_code == 204
    res = client.get("/api/v1/channels/", headers=auth_headers)
    assert res.json() == []


def test_cross_user_channel_not_found(client, auth_headers, admin_auth_headers):
    with _patched():
        created = client.post(
            "/api/v1/channels/",
            json={"url": "https://youtube.com/@test"},
            headers=auth_headers,
        ).json()
    res = client.get(
        f"/api/v1/channels/{created['id']}", headers=admin_auth_headers
    )
    assert res.status_code == 404
    res = client.delete(
        f"/api/v1/channels/{created['id']}", headers=admin_auth_headers
    )
    assert res.status_code == 404


def test_list_is_user_scoped(client, auth_headers, admin_auth_headers):
    with _patched():
        client.post(
            "/api/v1/channels/",
            json={"url": "https://youtube.com/@test"},
            headers=auth_headers,
        )
    res = client.get("/api/v1/channels/", headers=admin_auth_headers)
    assert res.json() == []
