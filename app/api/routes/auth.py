"""Auth routes — /register, /login, /refresh, /me."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and return their profile."""
    user = auth_service.register(db, payload)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with email + password.
    Returns access_token (30 min) and refresh_token (7 days).
    """
    return auth_service.login(db, payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new token pair."""
    return auth_service.refresh_tokens(db, payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
