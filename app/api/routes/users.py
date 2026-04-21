"""Protected user CRUD routes — list / create / update / delete."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),          # admin-only — listing users leaks directory info
):
    """Return all users. Requires admin privileges."""
    return user_service.get_all_users(db)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return a single user by ID."""
    return user_service.get_user_by_id(db, user_id)  # ← set breakpoint here


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Create a new user."""
    return user_service.create_user(db, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete a user by ID."""
    user_service.delete_user(db, user_id)
