"""Pydantic schemas for /ab-tests — title A/B experiments."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ABStatus = Literal["running", "completed", "cancelled"]
ABWinner = Literal["a", "b"]


class ABTestCreate(BaseModel):
    project_id: int
    title_a: str = Field(..., min_length=1, max_length=500)
    title_b: str = Field(..., min_length=1, max_length=500)
    notes: Optional[str] = None
    ends_at: Optional[datetime] = None


class ABTestUpdate(BaseModel):
    title_a: Optional[str] = Field(None, min_length=1, max_length=500)
    title_b: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[ABStatus] = None
    winner: Optional[ABWinner] = None
    notes: Optional[str] = None
    ends_at: Optional[datetime] = None


class ABTestResponse(BaseModel):
    id: int
    project_id: int
    title_a: str
    title_b: str
    status: ABStatus
    winner: Optional[ABWinner] = None
    notes: Optional[str] = None
    ends_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
