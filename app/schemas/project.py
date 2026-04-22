"""Pydantic schemas for /projects — create / update / response."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ProjectStatus = Literal["draft", "published", "archived"]


class ProjectCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    status: ProjectStatus = "draft"
    channel_id: Optional[int] = None
    idea_json: Optional[dict] = None
    script_json: Optional[dict] = None
    title_json: Optional[dict] = None
    seo_json: Optional[dict] = None
    slug: Optional[str] = Field(default=None, max_length=80)


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    status: Optional[ProjectStatus] = None
    channel_id: Optional[int] = None
    idea_json: Optional[dict] = None
    script_json: Optional[dict] = None
    title_json: Optional[dict] = None
    seo_json: Optional[dict] = None
    slug: Optional[str] = Field(default=None, max_length=80)


class ProjectResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    status: ProjectStatus
    channel_id: Optional[int] = None
    idea_json: Optional[dict] = None
    script_json: Optional[dict] = None
    title_json: Optional[dict] = None
    seo_json: Optional[dict] = None
    slug: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
