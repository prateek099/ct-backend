"""Routes: /trending — YouTube most-popular chart with 30-minute cache."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.trending import TrendingResponse
from app.services import trending_service

router = APIRouter(prefix="/trending", tags=["trending"])


@router.get("/", response_model=TrendingResponse)
async def get_trending(
    region: str = Query("US", min_length=2, max_length=10),
    category: Optional[str] = Query(None, max_length=10),
    max_results: int = Query(20, ge=1, le=50, alias="max"),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return trending_service.get_trending(
        db, region=region, category_id=category, max_results=max_results
    )
