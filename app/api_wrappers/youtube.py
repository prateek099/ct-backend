"""
YouTube Data API v3 wrapper.
Handles URL parsing and channel/video data fetching.
"""
import re
from urllib.parse import urlparse, parse_qs
from typing import Optional, Tuple

from googleapiclient.discovery import build
from loguru import logger

from app.core.config import settings
from app.core.exceptions import AppError, BadRequestError


def _get_service():
    """Build and return an authenticated YouTube API service client."""
    if not settings.youtube_api_key:
        logger.error("YOUTUBE_API_KEY is not configured — set it in .env")
        raise AppError("Internal server error")
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


def fetch_trending_videos(
    region: str = "US",
    category_id: Optional[str] = None,
    max_results: int = 20,
) -> list[dict]:
    """Fetch YouTube's most-popular chart for a region/category."""
    logger.info(
        "Fetching YouTube trending",
        region=region,
        category_id=category_id,
        max_results=max_results,
    )
    try:
        service = _get_service()
        params = {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": max(1, min(max_results, 50)),
        }
        if category_id:
            params["videoCategoryId"] = category_id

        resp = service.videos().list(**params).execute()
        items = resp.get("items", [])

        results: list[dict] = []
        for v in items:
            snippet = v.get("snippet", {})
            stats = v.get("statistics", {})
            content = v.get("contentDetails", {})
            results.append({
                "id": v.get("id", ""),
                "title": snippet.get("title", ""),
                "channel_name": snippet.get("channelTitle", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "published_at": snippet.get("publishedAt", ""),
                "duration_seconds": _parse_duration_seconds(
                    content.get("duration", "")
                ),
                "thumbnail_url": snippet.get("thumbnails", {})
                .get("high", {})
                .get("url", ""),
            })
        return results
    except (BadRequestError, AppError):
        raise
    except Exception as e:
        logger.exception("YouTube trending fetch failed", region=region)
        raise AppError(f"YouTube API error: {e}")


def _extract_video_id(url: str) -> str:
    """Extract a YouTube video id from a URL or raw id."""
    url = url.strip()
    # Prateek: Raw 11-char video id passed directly.
    if re.match(r"^[\w-]{11}$", url):
        return url
    identifier_type, value = parse_youtube_url(url)
    if identifier_type != "video_id":
        raise BadRequestError(
            "URL must point to a YouTube video (watch?v=..., youtu.be/..., or /shorts/...)."
        )
    return value


def fetch_video_thumbnails(url: str) -> dict:
    """
    Build the set of public YouTube thumbnail URLs for a video, plus light metadata.

    Returns:
        {
            video_id, title, channel_name,
            thumbnails: {default, medium, high, standard, maxres},
        }

    Missing metadata is returned as empty strings rather than raising — the
    thumbnail URLs themselves always resolve for public videos.
    """
    video_id = _extract_video_id(url)

    # Prateek: Public thumbnail URL scheme — no API call needed for these.
    thumbnails = {
        "default": f"https://i.ytimg.com/vi/{video_id}/default.jpg",
        "medium": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
        "high": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "standard": f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg",
        "maxres": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
    }

    title = ""
    channel_name = ""
    try:
        service = _get_service()
        resp = service.videos().list(part="snippet", id=video_id).execute()
        items = resp.get("items", [])
        if items:
            snip = items[0]["snippet"]
            title = snip.get("title", "")
            channel_name = snip.get("channelTitle", "")
    except AppError:
        # Prateek: No API key configured — still return the URLs; metadata is optional.
        logger.warning("Thumbnail metadata skipped — YOUTUBE_API_KEY missing")
    except Exception:
        logger.exception("Thumbnail metadata fetch failed", video_id=video_id)

    return {
        "video_id": video_id,
        "title": title,
        "channel_name": channel_name,
        "thumbnails": thumbnails,
    }
