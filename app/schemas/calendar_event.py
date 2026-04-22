"""Pydantic schemas for /calendar — content calendar events."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

EventType = Literal["record", "edit", "publish", "custom"]


class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    event_type: EventType
    scheduled_for: datetime
    project_id: Optional[int] = None
    notes: Optional[str] = None
    recurrence_rule: Optional[str] = None


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    event_type: Optional[EventType] = None
    scheduled_for: Optional[datetime] = None
    project_id: Optional[int] = None
    notes: Optional[str] = None
    recurrence_rule: Optional[str] = None


class CalendarEventResponse(BaseModel):
    id: int
    title: str
    event_type: EventType
    scheduled_for: datetime
    project_id: Optional[int] = None
    notes: Optional[str] = None
    recurrence_rule: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
