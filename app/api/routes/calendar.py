"""Routes: /calendar — per-user content calendar events."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.calendar_event import (
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
)
from app.services import calendar_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("/", response_model=CalendarEventResponse, status_code=201)
async def create_event(
    payload: CalendarEventCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return calendar_service.create_event(db, user, payload)


@router.get("/", response_model=list[CalendarEventResponse])
async def list_events(
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return calendar_service.list_events(db, user, from_date=from_, to_date=to)


@router.get("/{event_id}", response_model=CalendarEventResponse)
async def get_event(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return calendar_service.get_event(db, user, event_id)


@router.patch("/{event_id}", response_model=CalendarEventResponse)
async def update_event(
    event_id: int,
    payload: CalendarEventUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return calendar_service.update_event(db, user, event_id, payload)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    calendar_service.delete_event(db, user, event_id)
