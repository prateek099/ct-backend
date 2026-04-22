"""Tests for GET /api/v1/trending."""
from unittest.mock import patch


TRENDING_PAYLOAD = [
    {
        "id": "v1",
        "title": "Trending One",
        "channel_name": "Channel A",
        "view_count": 10_000,
        "like_count": 500,
        "comment_count": 20,
        "published_at": "2026-04-20T00:00:00Z",
        "duration_seconds": 240,
        "thumbnail_url": "https://example.com/v1.jpg",
    },
    {
        "id": "v2",
        "title": "Trending Two",
        "channel_name": "Channel B",
        "view_count": 5_000,
        "like_count": 200,
        "comment_count": 10,
        "published_at": "2026-04-20T00:00:00Z",
        "duration_seconds": 120,
        "thumbnail_url": "https://example.com/v2.jpg",
    },
]


def _patched(payload=None):
    return patch(
        "app.services.trending_service.fetch_trending_videos",
        return_value=payload if payload is not None else TRENDING_PAYLOAD,
    )


def test_unauth_blocked(client):
    res = client.get("/api/v1/trending/")
    assert res.status_code == 401


def test_initial_fetch_is_uncached(client, auth_headers):
    with _patched() as mock_fetch:
        res = client.get(
            "/api/v1/trending/?region=US", headers=auth_headers
        )
    assert res.status_code == 200
    body = res.json()
    assert body["region"] == "US"
    assert body["cached"] is False
    assert len(body["videos"]) == 2
    assert body["videos"][0]["id"] == "v1"
    assert mock_fetch.call_count == 1


def test_second_call_within_ttl_is_cached(client, auth_headers):
    with _patched() as mock_fetch:
        client.get("/api/v1/trending/?region=US", headers=auth_headers)
        res = client.get("/api/v1/trending/?region=US", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["cached"] is True
    # Prateek: Upstream should only be hit once — second call served from cache.
    assert mock_fetch.call_count == 1


def test_different_region_bypasses_cache(client, auth_headers):
    with _patched() as mock_fetch:
        client.get("/api/v1/trending/?region=US", headers=auth_headers)
        client.get("/api/v1/trending/?region=GB", headers=auth_headers)
    # Prateek: Different region — unique (region, category_id) row, another upstream call.
    assert mock_fetch.call_count == 2


def test_category_filter_separate_cache(client, auth_headers):
    with _patched() as mock_fetch:
        client.get("/api/v1/trending/?region=US", headers=auth_headers)
        client.get(
            "/api/v1/trending/?region=US&category=10", headers=auth_headers
        )
    assert mock_fetch.call_count == 2


def test_max_param_limits_response(client, auth_headers):
    with _patched():
        res = client.get(
            "/api/v1/trending/?region=US&max=1", headers=auth_headers
        )
    assert len(res.json()["videos"]) == 1


def test_invalid_max_rejected(client, auth_headers):
    res = client.get(
        "/api/v1/trending/?region=US&max=0", headers=auth_headers
    )
    assert res.status_code == 422
