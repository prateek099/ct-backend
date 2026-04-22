"""Routes: /ideas — user's saved idea bank."""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.saved_idea import SavedIdeaCreate, SavedIdeaResponse
from app.services import saved_idea_service

router = APIRouter(prefix="/ideas", tags=["ideas"])


@router.post("/", response_model=SavedIdeaResponse, status_code=201)
async def create_saved_idea(
    payload: SavedIdeaCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return saved_idea_service.create_idea(db, user, payload)


@router.get("/", response_model=list[SavedIdeaResponse])
async def list_saved_ideas(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return saved_idea_service.list_ideas(db, user, limit=limit, offset=offset)


@router.delete("/{idea_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_idea(
    idea_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved_idea_service.delete_idea(db, user, idea_id)
