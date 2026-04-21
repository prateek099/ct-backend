"""Routes: YouTube channel/video lookup endpoints."""
from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from typing import List

from app.api.deps import require_valid_token
from app.api_wrappers.youtube import fetch_channel_data
from app.core.exceptions import AppError, BadRequestError

router = APIRouter()


# ── Pydantic models ────────────────────────────────────────────────────────────

class ChannelRequest(BaseModel):
    url: str = Field(
        ...,
        description="YouTube channel URL, @handle, video URL, or direct channel ID",
        examples=["https://www.youtube.com/@mkbhd"],
    )


class VideoSummary(BaseModel):
    id: str
    title: str
    description: str
    view_count: int
    like_count: int
    comment_count: int
    duration_seconds: int
    published_at: str


class ChannelDataResponse(BaseModel):
    channel_id: str
    channel_name: str
    handle: str
    description: str
    subscriber_count: int
    total_views: int
    video_count: int
    thumbnail_url: str
    recent_videos: List[VideoSummary]
    average_duration_seconds: int


# ── endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/yt/channel",
    tags=["youtube"],
    response_model=ChannelDataResponse,
    summary="Fetch YouTube channel data",
    description=(
        "Accepts any YouTube URL (channel page, @handle, video link, or raw channel ID) "
        "and returns channel statistics plus the 20 most recent videos with their metrics."
    ),
    responses={
        400: {"description": "Invalid or unparseable YouTube URL"},
        500: {"description": "YouTube API error"},
    },
)
def get_channel_data(
    request: ChannelRequest,
    _token: dict = Depends(require_valid_token),
) -> ChannelDataResponse:
    if not request.url.strip():
        raise BadRequestError("URL cannot be empty")

    logger.info("YouTube channel fetch", url=request.url[:80])
    data = fetch_channel_data(request.url)
    return ChannelDataResponse(**data)
