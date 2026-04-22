"""Channel service — persists per-user YouTube channel snapshots with 24h refresh."""
from datetime import datetime, timedelta

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
