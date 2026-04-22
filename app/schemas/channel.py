"""Pydantic schemas for /channels — cached YouTube channel snapshots."""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ChannelCreate(BaseModel):
    url: str = Field(..., description="YouTube channel URL, @handle, video URL, or ID")


class ChannelResponse(BaseModel):
    id: int
    youtube_channel_id: str
    channel_name: str
    handle: Optional[str] = None
    description: Optional[str] = None
    subscriber_count: Optional[int] = None
    total_views: Optional[int] = None
    video_count: Optional[int] = None
    thumbnail_url: Optional[str] = None
    recent_videos: list[Any] = Field(default_factory=list)
    average_duration_seconds: Optional[int] = None
    last_refreshed_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, row) -> "ChannelResponse":
        return cls(
            id=row.id,
            youtube_channel_id=row.youtube_channel_id,
            channel_name=row.channel_name,
            handle=row.handle,
            description=row.description,
            subscriber_count=row.subscriber_count,
            total_views=row.total_views,
            video_count=row.video_count,
            thumbnail_url=row.thumbnail_url,
            recent_videos=row.recent_videos_json or [],
            average_duration_seconds=row.average_duration_seconds,
            last_refreshed_at=row.last_refreshed_at,
            created_at=row.created_at,
        )


class TopVideo(BaseModel):
    id: str
    title: str
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int
    published_at: str


class ChannelStatsResponse(BaseModel):
    channel_id: int
    channel_name: str
    subscriber_count: Optional[int] = None
    total_views: Optional[int] = None
    video_count: Optional[int] = None
    average_duration_seconds: Optional[int] = None
    sample_size: int = Field(
        ...,
        description="Number of recent videos the aggregates are computed over.",
    )
    recent_views_sum: int = 0
    recent_likes_sum: int = 0
    recent_comments_sum: int = 0
    average_views_per_video: int = 0
    engagement_rate: float = Field(
        0.0,
        description="(likes + comments) / views across the sample, 0.0 if no views.",
    )
    videos_per_week: float = Field(
        0.0,
        description="Publish cadence across the sample window (first → last upload).",
    )
    top_videos: List[TopVideo] = Field(default_factory=list)
    last_refreshed_at: datetime
