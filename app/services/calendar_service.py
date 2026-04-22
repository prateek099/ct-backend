"""Calendar service — per-user CRUD with date-range filter."""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.api.deps import get_owned_or_404
from app.models.calendar_event import CalendarEvent
from app.models.user import User
from app.schemas.calendar_event import CalendarEventCreate, CalendarEventUpdate


def create_event(
    db: Session, user: User, payload: CalendarEventCreate
) -> CalendarEvent:
    event = CalendarEvent(user_id=user.id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(
    db: Session,
    user: User,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> list[CalendarEvent]:
    q = db.query(CalendarEvent).filter(CalendarEvent.user_id == user.id)
    if from_date is not None:
        q = q.filter(CalendarEvent.scheduled_for >= from_date)
    if to_date is not None:
        q = q.filter(CalendarEvent.scheduled_for <= to_date)
    return q.order_by(CalendarEvent.scheduled_for.asc()).all()


def get_event(db: Session, user: User, event_id: int) -> CalendarEvent:
    return get_owned_or_404(db, CalendarEvent, event_id, user)


def update_event(
    db: Session, user: User, event_id: int, payload: CalendarEventUpdate
) -> CalendarEvent:
    event = get_owned_or_404(db, CalendarEvent, event_id, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(event, k, v)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, user: User, event_id: int) -> None:
    event = get_owned_or_404(db, CalendarEvent, event_id, user)
    db.delete(event)
    db.commit()
