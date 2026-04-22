"""Routes: /ab-tests — title A/B experiments per project."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.ab_test import ABTestCreate, ABTestResponse, ABTestUpdate
from app.services import ab_test_service

router = APIRouter(prefix="/ab-tests", tags=["ab-tests"])


@router.post("/", response_model=ABTestResponse, status_code=201)
async def create_test(
    payload: ABTestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ab_test_service.create_ab_test(db, user, payload)


@router.get("/", response_model=list[ABTestResponse])
async def list_tests(
    project_id: Optional[int] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ab_test_service.list_ab_tests(
        db, user, project_id=project_id, status=status_
    )


@router.get("/{test_id}", response_model=ABTestResponse)
async def get_test(
    test_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ab_test_service.get_ab_test(db, user, test_id)


@router.patch("/{test_id}", response_model=ABTestResponse)
async def update_test(
    test_id: int,
    payload: ABTestUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ab_test_service.update_ab_test(db, user, test_id, payload)


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(
    test_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ab_test_service.delete_ab_test(db, user, test_id)
