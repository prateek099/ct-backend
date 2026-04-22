"""Tests for GET /api/v1/channels/{id}/stats — aggregates cached channel data."""
from unittest.mock import patch


CHANNEL_PAYLOAD = {
    "channel_id": "UC-stats",
    "channel_name": "Stats Channel",
    "handle": "@stats",
    "description": "",
    "subscriber_count": 10_000,
    "total_views": 500_000,
    "video_count": 100,
    "thumbnail_url": "https://example.com/s.jpg",
    "recent_videos": [
        {
            "id": "v1",
            "title": "Video 1",
            "view_count": 10_000,
            "like_count": 500,
            "comment_count": 50,
            "duration_seconds": 600,
            "published_at": "2026-04-20T00:00:00Z",
        },
        {
            "id": "v2",
            "title": "Video 2",
            "view_count": 5_000,
            "like_count": 100,
            "comment_count": 10,
            "duration_seconds": 300,
            "published_at": "2026-04-13T00:00:00Z",
        },
        {
            "id": "v3",
            "title": "Video 3",
            "view_count": 20_000,
            "like_count": 800,
            "comment_count": 120,
            "duration_seconds": 900,
            "published_at": "2026-04-06T00:00:00Z",
        },
    ],
    "average_duration_seconds": 600,
}


def _patched():
    return patch(
        "app.services.channel_service.fetch_channel_data",
        return_value=CHANNEL_PAYLOAD,
    )


def _create_channel(client, headers):
    with _patched():
        return client.post(
            "/api/v1/channels/",
            json={"url": "https://youtube.com/@stats"},
            headers=headers,
        ).json()


def test_unauth_blocked(client):
    res = client.get("/api/v1/channels/1/stats")
    assert res.status_code == 401


def test_stats_aggregates_recent_videos(client, auth_headers):
    created = _create_channel(client, auth_headers)
    res = client.get(
        f"/api/v1/channels/{created['id']}/stats", headers=auth_headers
    )
    assert res.status_code == 200
    body = res.json()
    assert body["channel_id"] == created["id"]
    assert body["channel_name"] == "Stats Channel"
    assert body["sample_size"] == 3
    assert body["recent_views_sum"] == 35_000
    assert body["recent_likes_sum"] == 1_400
    assert body["recent_comments_sum"] == 180
    assert body["average_views_per_video"] == 35_000 // 3
    # Prateek: (likes+comments)/views = 1580/35000 ≈ 0.0451
    assert abs(body["engagement_rate"] - 0.0451) < 0.001


def test_stats_top_videos_sorted_by_views(client, auth_headers):
    created = _create_channel(client, auth_headers)
    res = client.get(
        f"/api/v1/channels/{created['id']}/stats", headers=auth_headers
    )
    top = res.json()["top_videos"]
    assert [v["id"] for v in top] == ["v3", "v1", "v2"]
    assert top[0]["view_count"] == 20_000


def test_stats_videos_per_week_from_span(client, auth_headers):
    created = _create_channel(client, auth_headers)
    res = client.get(
        f"/api/v1/channels/{created['id']}/stats", headers=auth_headers
    )
    # Prateek: 3 videos spanning exactly 14 days → 1.5 per week.
    assert res.json()["videos_per_week"] == 1.5


def test_stats_cross_user_blocked(client, auth_headers, admin_auth_headers):
    created = _create_channel(client, auth_headers)
    res = client.get(
        f"/api/v1/channels/{created['id']}/stats", headers=admin_auth_headers
    )
    assert res.status_code == 404


def test_stats_unknown_channel_404(client, auth_headers):
    res = client.get("/api/v1/channels/99999/stats", headers=auth_headers)
    assert res.status_code == 404


def test_stats_empty_recent_videos(client, auth_headers):
    payload = {**CHANNEL_PAYLOAD, "recent_videos": []}
    with patch(
        "app.services.channel_service.fetch_channel_data",
        return_value=payload,
    ):
        created = client.post(
            "/api/v1/channels/",
            json={"url": "https://youtube.com/@stats"},
            headers=auth_headers,
        ).json()
    res = client.get(
        f"/api/v1/channels/{created['id']}/stats", headers=auth_headers
    )
    assert res.status_code == 200
    body = res.json()
    assert body["sample_size"] == 0
    assert body["recent_views_sum"] == 0
    assert body["average_views_per_video"] == 0
    assert body["engagement_rate"] == 0.0
    assert body["videos_per_week"] == 0.0
    assert body["top_videos"] == []
