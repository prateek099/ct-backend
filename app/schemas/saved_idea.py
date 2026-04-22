"""Pydantic schemas for /ideas — saved idea bank."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SavedIdeaCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    hook: Optional[str] = None
    angle: Optional[str] = Field(None, max_length=100)
    format: Optional[str] = Field(None, max_length=100)
    reasoning: Optional[str] = None
    source_prompt: Optional[str] = None
    source_project_id: Optional[int] = None


class SavedIdeaResponse(BaseModel):
    id: int
    title: str
    hook: Optional[str] = None
    angle: Optional[str] = None
    format: Optional[str] = None
    reasoning: Optional[str] = None
    source_prompt: Optional[str] = None
    source_project_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}
