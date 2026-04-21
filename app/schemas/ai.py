"""Shared Pydantic schemas for AI route payloads."""
from typing import List

from pydantic import BaseModel


class ChannelContext(BaseModel):
    """
    Optional YouTube-channel context passed to AI endpoints.

    Every field defaults so each route can supply only what it needs.
    `average_duration_seconds` default of 600 preserves the legacy script-generator
    assumption (~10 min video) when the frontend omits the field.
    """

    channel_name: str = ""
    handle: str = ""
    description: str = ""
    subscriber_count: int = 0
    average_duration_seconds: int = 600
    recent_video_titles: List[str] = []
