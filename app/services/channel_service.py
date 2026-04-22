"""Channel service — persists per-user YouTube channel snapshots with 24h refresh."""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.api.deps import get_owned_or_404
from app.api_wrappers.youtube import fetch_channel_data
from app.models.channel import Channel
from app.models.user import User

# Prateek: 24h cache window matches the feature plan — balances fresh data with
# YT Data API quota (10k units/day across the whole app).
CACHE_TTL = timedelta(hours=24)


def _apply_payload(row: Channel, payload: dict) -> None:
    row.youtube_channel_id = payload["channel_id"]
    row.channel_name = payload["channel_name"]
    row.handle = payload.get("handle")
    row.description = payload.get("description")
    row.subscriber_count = payload.get("subscriber_count")
    row.total_views = payload.get("total_views")
    row.video_count = payload.get("video_count")
    row.thumbnail_url = payload.get("thumbnail_url")
    row.recent_videos_json = payload.get("recent_videos") or []
    row.average_duration_seconds = payload.get("average_duration_seconds")
    row.last_refreshed_at = datetime.utcnow()


def upsert_from_url(db: Session, user: User, url: str) -> Channel:
    """Fetch from YT, create or update the user's saved channel row."""
    payload = fetch_channel_data(url)
    youtube_channel_id = payload["channel_id"]

    existing = (
        db.query(Channel)
        .filter(
            Channel.user_id == user.id,
            Channel.youtube_channel_id == youtube_channel_id,
        )
        .first()
    )
    if existing is None:
        existing = Channel(user_id=user.id, youtube_channel_id=youtube_channel_id, channel_name=payload["channel_name"])
        db.add(existing)

    _apply_payload(existing, payload)
    db.commit()
    db.refresh(existing)
    return existing


def list_channels(db: Session, user: User) -> list[Channel]:
    return (
        db.query(Channel)
        .filter(Channel.user_id == user.id)
        .order_by(Channel.created_at.desc())
        .all()
    )


def get_channel(db: Session, user: User, channel_id: int) -> Channel:
    return get_owned_or_404(db, Channel, channel_id, user)


def refresh_channel(db: Session, user: User, channel_id: int) -> Channel:
    row = get_owned_or_404(db, Channel, channel_id, user)
    payload = fetch_channel_data(row.handle or row.youtube_channel_id)
    _apply_payload(row, payload)
    db.commit()
    db.refresh(row)
    return row


def delete_channel(db: Session, user: User, channel_id: int) -> None:
    row = get_owned_or_404(db, Channel, channel_id, user)
    db.delete(row)
    db.commit()


def is_stale(row: Channel) -> bool:
    return datetime.utcnow() - row.last_refreshed_at > CACHE_TTL


def _parse_iso(ts: str) -> datetime | None:
    # Prateek: YT returns RFC 3339 (…Z). fromisoformat handles the offset form
    # directly in 3.11+; we strip the trailing Z for 3.10 compatibility.
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def compute_stats(row: Channel) -> dict[str, Any]:
    """Aggregate the row's cached recent_videos into dashboard stats.

    No network calls — reads straight from the Channel row, so the 24h cache
    TTL governs freshness. Returns a plain dict suitable for ChannelStatsResponse.
    """
    videos: list[dict[str, Any]] = list(row.recent_videos_json or [])
    sample_size = len(videos)

    views_sum = sum(int(v.get("view_count", 0) or 0) for v in videos)
    likes_sum = sum(int(v.get("like_count", 0) or 0) for v in videos)
    comments_sum = sum(int(v.get("comment_count", 0) or 0) for v in videos)

    avg_views = views_sum // sample_size if sample_size else 0
    engagement = (likes_sum + comments_sum) / views_sum if views_sum else 0.0

    # Prateek: Publish cadence from first → last upload in the sample window.
    # Needs ≥2 dated videos to compute a span; otherwise return 0.
    dated = sorted(
        (p for p in (_parse_iso(v.get("published_at", "")) for v in videos) if p),
        reverse=True,
    )
    videos_per_week = 0.0
    if len(dated) >= 2:
        span = dated[0] - dated[-1]
        weeks = span.total_seconds() / (7 * 86_400)
        if weeks > 0:
            videos_per_week = round(len(dated) / weeks, 2)

    top_videos = sorted(
        videos,
        key=lambda v: int(v.get("view_count", 0) or 0),
        reverse=True,
    )[:5]

    return {
        "channel_id": row.id,
        "channel_name": row.channel_name,
        "subscriber_count": row.subscriber_count,
        "total_views": row.total_views,
        "video_count": row.video_count,
        "average_duration_seconds": row.average_duration_seconds,
        "sample_size": sample_size,
        "recent_views_sum": views_sum,
        "recent_likes_sum": likes_sum,
        "recent_comments_sum": comments_sum,
        "average_views_per_video": avg_views,
        "engagement_rate": round(engagement, 4),
        "videos_per_week": videos_per_week,
        "top_videos": [
            {
                "id": v.get("id", ""),
                "title": v.get("title", ""),
                "view_count": int(v.get("view_count", 0) or 0),
                "like_count": int(v.get("like_count", 0) or 0),
                "comment_count": int(v.get("comment_count", 0) or 0),
                "duration_seconds": int(v.get("duration_seconds", 0) or 0),
                "published_at": v.get("published_at", ""),
            }
            for v in top_videos
        ],
        "last_refreshed_at": row.last_refreshed_at,
    }


def get_stats(db: Session, user: User, channel_id: int) -> dict[str, Any]:
    row = get_owned_or_404(db, Channel, channel_id, user)
    return compute_stats(row)
