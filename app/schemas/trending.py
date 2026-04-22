"""Pydantic schemas for /trending."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TrendingVideo(BaseModel):
    id: str
    title: str
    channel_name: str
    view_count: int
    like_count: int
    comment_count: int
    published_at: str
    duration_seconds: int
    thumbnail_url: str


class TrendingResponse(BaseModel):
    region: str
    category_id: Optional[str] = None
    fetched_at: datetime
    cached: bool
    videos: List[TrendingVideo]
