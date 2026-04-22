"""Tests for POST /api/v1/yt/thumbnails."""
from unittest.mock import patch


def _mock_service(title: str = "Never Gonna Give You Up", channel: str = "Rick"):
    # Prateek: Mimic the googleapiclient fluent builder returned by build(...).
    class _Exec:
        def __init__(self, items):
            self._items = items

        def execute(self):
            return {"items": self._items}

    class _Videos:
        def list(self, **_):
            return _Exec([
                {"snippet": {"title": title, "channelTitle": channel}}
            ])

    class _Service:
        def videos(self):
            return _Videos()

    return _Service()


def test_unauth_blocked(client):
    res = client.post("/api/v1/yt/thumbnails", json={"url": "dQw4w9WgXcQ"})
    assert res.status_code == 401


def test_thumbnails_from_watch_url(client, auth_headers):
    with patch(
        "app.api_wrappers.youtube._get_service", return_value=_mock_service()
    ):
        res = client.post(
            "/api/v1/yt/thumbnails",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            headers=auth_headers,
        )
    assert res.status_code == 200
    body = res.json()
    assert body["video_id"] == "dQw4w9WgXcQ"
    assert body["title"] == "Never Gonna Give You Up"
    assert body["channel_name"] == "Rick"
    assert body["thumbnails"]["maxres"].endswith("/dQw4w9WgXcQ/maxresdefault.jpg")
    assert body["thumbnails"]["default"].endswith("/dQw4w9WgXcQ/default.jpg")


def test_thumbnails_from_short_url(client, auth_headers):
    with patch(
        "app.api_wrappers.youtube._get_service", return_value=_mock_service()
    ):
        res = client.post(
            "/api/v1/yt/thumbnails",
            json={"url": "https://youtu.be/dQw4w9WgXcQ"},
            headers=auth_headers,
        )
    assert res.status_code == 200
    assert res.json()["video_id"] == "dQw4w9WgXcQ"


def test_thumbnails_from_shorts_url(client, auth_headers):
    with patch(
        "app.api_wrappers.youtube._get_service", return_value=_mock_service()
    ):
        res = client.post(
            "/api/v1/yt/thumbnails",
            json={"url": "https://www.youtube.com/shorts/abcDEF12345"},
            headers=auth_headers,
        )
    assert res.status_code == 200
    assert res.json()["video_id"] == "abcDEF12345"


def test_thumbnails_from_raw_id(client, auth_headers):
    with patch(
        "app.api_wrappers.youtube._get_service", return_value=_mock_service()
    ):
        res = client.post(
            "/api/v1/yt/thumbnails",
            json={"url": "dQw4w9WgXcQ"},
            headers=auth_headers,
        )
    assert res.status_code == 200
    assert res.json()["video_id"] == "dQw4w9WgXcQ"


def test_channel_url_is_rejected(client, auth_headers):
    res = client.post(
        "/api/v1/yt/thumbnails",
        json={"url": "https://www.youtube.com/@mkbhd"},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_empty_url_is_rejected(client, auth_headers):
    res = client.post(
        "/api/v1/yt/thumbnails", json={"url": "   "}, headers=auth_headers
    )
    assert res.status_code == 400


def test_metadata_missing_still_returns_urls(client, auth_headers):
    # Prateek: When _get_service raises (no API key), the endpoint still returns URLs
    # with empty title/channel_name.
    from app.core.exceptions import AppError

    with patch(
        "app.api_wrappers.youtube._get_service",
        side_effect=AppError("Internal server error"),
    ):
        res = client.post(
            "/api/v1/yt/thumbnails",
            json={"url": "dQw4w9WgXcQ"},
            headers=auth_headers,
        )
    assert res.status_code == 200
    body = res.json()
    assert body["video_id"] == "dQw4w9WgXcQ"
    assert body["title"] == ""
    assert body["channel_name"] == ""
