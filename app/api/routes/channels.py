"""Routes: /channels — per-user cached YouTube channel snapshots."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.channel import ChannelCreate, ChannelResponse
from app.services import channel_service

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/", response_model=list[ChannelResponse])
async def list_channels(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [
        ChannelResponse.from_orm_row(row)
        for row in channel_service.list_channels(db, user)
    ]


@router.post("/", response_model=ChannelResponse, status_code=201)
async def create_channel(
    payload: ChannelCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = channel_service.upsert_from_url(db, user, payload.url)
    return ChannelResponse.from_orm_row(row)


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = channel_service.get_channel(db, user, channel_id)
    return ChannelResponse.from_orm_row(row)


@router.post("/{channel_id}/refresh", response_model=ChannelResponse)
async def refresh_channel(
    channel_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = channel_service.refresh_channel(db, user, channel_id)
    return ChannelResponse.from_orm_row(row)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    channel_service.delete_channel(db, user, channel_id)
