"""Tests for POST /api/v1/yt/subtitles."""
from dataclasses import dataclass
from unittest.mock import patch


@dataclass
class _Snippet:
    text: str
    start: float
    duration: float


class _FetchedTranscript:
    def __init__(self, snippets, lang="en"):
        self._snippets = snippets
        self.language_code = lang

    def __iter__(self):
        return iter(self._snippets)


def _fake_transcript(lang: str = "en"):
    return _FetchedTranscript(
        [
            _Snippet(text="Hello world", start=0.0, duration=1.5),
            _Snippet(text="Second line", start=1.5, duration=2.0),
        ],
        lang=lang,
    )


def test_unauth_blocked(client):
    res = client.post("/api/v1/yt/subtitles", json={"url": "dQw4w9WgXcQ"})
    assert res.status_code == 401


def test_fetch_subtitles_happy_path(client, auth_headers):
    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi.fetch",
        return_value=_fake_transcript(),
    ):
        res = client.post(
            "/api/v1/yt/subtitles",
            json={"url": "https://youtu.be/dQw4w9WgXcQ"},
            headers=auth_headers,
        )
    assert res.status_code == 200
    body = res.json()
    assert body["video_id"] == "dQw4w9WgXcQ"
    assert body["language"] == "en"
    assert len(body["entries"]) == 2
    assert body["entries"][0]["text"] == "Hello world"
    assert "Hello world" in body["srt"]
    assert body["srt"].startswith("1\n")
    assert body["vtt"].startswith("WEBVTT")
    # Prateek: SRT uses comma ms separator; VTT uses dot.
    assert "00:00:00,000 --> 00:00:01,500" in body["srt"]
    assert "00:00:00.000 --> 00:00:01.500" in body["vtt"]


def test_no_transcript_found_returns_500_app_error(client, auth_headers):
    from youtube_transcript_api._errors import NoTranscriptFound

    # Prateek: NoTranscriptFound signature: (video_id, requested_language_codes, transcript_data)
    exc = NoTranscriptFound.__new__(NoTranscriptFound)
    exc.args = ("no transcript",)

    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi.fetch",
        side_effect=exc,
    ):
        res = client.post(
            "/api/v1/yt/subtitles",
            json={"url": "dQw4w9WgXcQ"},
            headers=auth_headers,
        )
    # Prateek: AppError maps to 500 by default — good enough signal; detail carries reason.
    assert res.status_code == 500
    assert "subtitles" in res.json()["error"]["detail"].lower()


def test_scraper_breakage_returns_502(client, auth_headers):
    from youtube_transcript_api._errors import CouldNotRetrieveTranscript

    exc = CouldNotRetrieveTranscript.__new__(CouldNotRetrieveTranscript)
    exc.args = ("blocked",)

    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi.fetch",
        side_effect=exc,
    ):
        res = client.post(
            "/api/v1/yt/subtitles",
            json={"url": "dQw4w9WgXcQ"},
            headers=auth_headers,
        )
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "SUBTITLES_UPSTREAM_ERROR"


def test_invalid_url_rejected(client, auth_headers):
    res = client.post(
        "/api/v1/yt/subtitles",
        json={"url": "https://www.youtube.com/@mkbhd"},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_language_parameter_forwarded(client, auth_headers):
    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi.fetch",
        return_value=_fake_transcript(lang="de"),
    ) as mock_fetch:
        res = client.post(
            "/api/v1/yt/subtitles",
            json={"url": "dQw4w9WgXcQ", "language": "de"},
            headers=auth_headers,
        )
    assert res.status_code == 200
    assert res.json()["language"] == "de"
    # Prateek: Confirm the language prefs were forwarded.
    _, kwargs = mock_fetch.call_args
    assert kwargs.get("languages") == ("de",) or mock_fetch.call_args[0][-1] == ("de",)
