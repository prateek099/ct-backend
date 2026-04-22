"""Trending service — wraps YouTube mostPopular with a 30-minute cache."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.api_wrappers.youtube import fetch_trending_videos
from app.models.trending_cache import TrendingCache

CACHE_TTL = timedelta(minutes=30)


def _is_fresh(row: TrendingCache) -> bool:
    # Prateek: server_default=func.now() leaves fetched_at as a naive datetime;
    # compare with utcnow() to match.
    return datetime.utcnow() - row.fetched_at < CACHE_TTL


def get_trending(
    db: Session,
    region: str,
    category_id: Optional[str],
    max_results: int,
) -> dict:
    """Return trending videos for (region, category_id), using cache when fresh."""
    region = (region or "US").upper()
    cat = (category_id or None)

    row = (
        db.query(TrendingCache)
        .filter(
            TrendingCache.region == region,
            TrendingCache.category_id == cat,
        )
        .first()
    )
    if row and _is_fresh(row):
        videos = (row.data or [])[:max_results]
        return {
            "region": region,
            "category_id": cat,
            "fetched_at": row.fetched_at,
            "cached": True,
            "videos": videos,
        }

    videos = fetch_trending_videos(
        region=region, category_id=cat, max_results=max_results
    )

    if row:
        row.data = videos
        row.fetched_at = datetime.utcnow()
    else:
        row = TrendingCache(
            region=region,
            category_id=cat,
            data=videos,
            fetched_at=datetime.utcnow(),
        )
        db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "region": region,
        "category_id": cat,
        "fetched_at": row.fetched_at,
        "cached": False,
        "videos": videos[:max_results],
    }
