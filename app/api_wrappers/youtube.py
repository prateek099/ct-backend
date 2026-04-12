"""
YouTube Data API v3 wrapper.
Handles URL parsing and channel/video data fetching.
"""
import re
from urllib.parse import urlparse, parse_qs
from typing import Tuple

from googleapiclient.discovery import build
from loguru import logger

from app.core.config import settings
from app.core.exceptions import AppError, BadRequestError


def _get_service():
    """Build and return an authenticated YouTube API service client."""
    if not settings.youtube_api_key:
        raise AppError("YOUTUBE_API_KEY is not configured")
    return build("youtube", "v3", developerKey=settings.youtube_api_key)


def _parse_duration_seconds(iso_duration: str) -> int:
    """Convert ISO 8601 duration (PT1H2M3S) to total seconds."""
    pattern = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
    m = pattern.match(iso_duration or "")
    if not m:
        return 0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def parse_youtube_url(url: str) -> Tuple[str, str]:
    """
    Parse a YouTube URL and return (identifier_type, value).

    identifier_type is one of: 'channel_id', 'handle', 'username', 'video_id'
    """
    url = url.strip()
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    # Prateek: Direct channel ID passed (UC...)
    if re.match(r"^UC[\w-]{22}$", url):
        return ("channel_id", url)

    # youtube.com/channel/UCxxx
    m = re.match(r"^/channel/(UC[\w-]+)$", path)
    if m:
        return ("channel_id", m.group(1))

    # youtube.com/@handle
    m = re.match(r"^/@([\w.]+)$", path)
    if m:
        return ("handle", m.group(1))

    # youtube.com/c/customname
    m = re.match(r"^/c/([\w.]+)$", path)
    if m:
        return ("username", m.group(1))

    # youtube.com/user/username
    m = re.match(r"^/user/([\w.]+)$", path)
    if m:
        return ("username", m.group(1))

    # youtube.com/watch?v=VIDEO_ID
    qs = parse_qs(parsed.query)
    if "v" in qs:
        return ("video_id", qs["v"][0])

    # youtu.be/VIDEO_ID
    if "youtu.be" in parsed.netloc:
        video_id = path.lstrip("/")
        if video_id:
            return ("video_id", video_id)

    # youtube.com/shorts/VIDEO_ID
    m = re.match(r"^/shorts/([\w-]+)$", path)
    if m:
        return ("video_id", m.group(1))

    raise BadRequestError(f"Cannot parse YouTube URL: {url}")


def _resolve_channel_id(service, identifier_type: str, value: str) -> str:
    """Resolve any identifier type to a channel ID."""
    if identifier_type == "channel_id":
        return value

    if identifier_type == "handle":
        resp = service.channels().list(part="id", forHandle=value).execute()
        items = resp.get("items", [])
        if not items:
            raise BadRequestError(f"No channel found for handle @{value}")
        return items[0]["id"]

    if identifier_type == "username":
        resp = service.channels().list(part="id", forUsername=value).execute()
        items = resp.get("items", [])
        if not items:
            raise BadRequestError(f"No channel found for username {value}")
        return items[0]["id"]

    if identifier_type == "video_id":
        resp = service.videos().list(part="snippet", id=value).execute()
        items = resp.get("items", [])
        if not items:
            raise BadRequestError(f"Video not found: {value}")
        return items[0]["snippet"]["channelId"]

    raise BadRequestError(f"Unknown identifier type: {identifier_type}")


def fetch_channel_data(url: str) -> dict:
    """
    Fetch channel metadata and recent videos from a YouTube URL.

    Returns:
        {
            channel_id, channel_name, handle, description,
            subscriber_count, total_views, video_count, thumbnail_url,
            recent_videos: [{id, title, description, view_count, like_count,
                             comment_count, duration_seconds, published_at}],
            average_duration_seconds
        }
    """
    logger.info("Fetching YouTube channel data", url=url[:80])
    try:
        service = _get_service()
        identifier_type, value = parse_youtube_url(url)
        channel_id = _resolve_channel_id(service, identifier_type, value)

        # Prateek: Fetch channel details including contentDetails for uploads playlist
        ch_resp = service.channels().list(
            part="snippet,statistics,contentDetails",
            id=channel_id
        ).execute()
        ch_items = ch_resp.get("items", [])
        if not ch_items:
            raise BadRequestError(f"Channel not found: {channel_id}")

        channel = ch_items[0]
        snippet = channel["snippet"]
        stats = channel.get("statistics", {})
        uploads_playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]

        # Fetch recent 20 videos from uploads playlist
        pl_resp = service.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist,
            maxResults=20
        ).execute()
        pl_items = pl_resp.get("items", [])
        video_ids = [item["contentDetails"]["videoId"] for item in pl_items]

        # Prateek: Batch fetch stats and duration for all videos in one API call
        videos_detail: dict = {}
        if video_ids:
            v_resp = service.videos().list(
                part="statistics,contentDetails,snippet",
                id=",".join(video_ids)
            ).execute()
            for v in v_resp.get("items", []):
                videos_detail[v["id"]] = v

        recent_videos = []
        durations = []
        for item in pl_items:
            vid_id = item["contentDetails"]["videoId"]
            detail = videos_detail.get(vid_id, {})
            v_stats = detail.get("statistics", {})
            v_content = detail.get("contentDetails", {})
            v_snippet = detail.get("snippet", item.get("snippet", {}))
            duration_s = _parse_duration_seconds(v_content.get("duration", ""))
            if duration_s > 0:
                durations.append(duration_s)
            recent_videos.append({
                "id": vid_id,
                "title": v_snippet.get("title", ""),
                "description": (v_snippet.get("description", ""))[:300],
                "view_count": int(v_stats.get("viewCount", 0)),
                "like_count": int(v_stats.get("likeCount", 0)),
                "comment_count": int(v_stats.get("commentCount", 0)),
                "duration_seconds": duration_s,
                "published_at": v_snippet.get("publishedAt", ""),
            })

        avg_duration = int(sum(durations) / len(durations)) if durations else 0

        logger.info(
            "YouTube channel fetched",
            channel_id=channel_id,
            videos=len(recent_videos),
        )
        return {
            "channel_id": channel_id,
            "channel_name": snippet.get("title", ""),
            "handle": snippet.get("customUrl", ""),
            "description": (snippet.get("description", ""))[:500],
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "recent_videos": recent_videos,
            "average_duration_seconds": avg_duration,
        }
    except (BadRequestError, AppError):
        raise
    except Exception as e:
        logger.exception("YouTube API error", url=url[:80])
        raise AppError(f"YouTube API error: {e}")
