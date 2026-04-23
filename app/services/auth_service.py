"""Auth service — register, login, refresh_tokens, google_login. Raises AppError subclasses."""
import secrets
import httpx
from jose import jwt
from sqlalchemy.orm import Session
from app.core.config import settings

from app.core import messages
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.user_service import get_user_by_email


def register(db: Session, payload: RegisterRequest) -> User:
    if get_user_by_email(db, payload.email):
        raise ConflictError(messages.EMAIL_ALREADY_REGISTERED)
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, payload: LoginRequest) -> TokenResponse:
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError(messages.INVALID_CREDENTIALS)
    if not user.is_active:
        raise UnauthorizedError(messages.ACCOUNT_DISABLED)
    return TokenResponse(
        name=user.name,
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


def refresh_tokens(db: Session, refresh_token: str) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise UnauthorizedError(messages.TOKEN_INVALID_OR_EXPIRED)

    if payload.get("type") != "refresh":
        raise UnauthorizedError(messages.TOKEN_NOT_REFRESH)

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise UnauthorizedError(messages.USER_NOT_FOUND_OR_INACTIVE)

    return TokenResponse(
        name=user.name,
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


def google_login(db: Session, code: str) -> TokenResponse:
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    
    response = httpx.post(token_url, data=data)
    if response.status_code != 200:
        from loguru import logger
        logger.error(f"Google Token API failed: {response.text}")
        raise UnauthorizedError(f"Failed to authenticate with Google: {response.text}")
        
    tokens = response.json()
    id_token = tokens.get("id_token")
    if not id_token:
        raise UnauthorizedError("No ID token received from Google")
            
    # Decode ID token to get user info (no need to verify signature here as it came directly from Google)
    try:
        user_info = jwt.get_unverified_claims(id_token)
    except Exception:
        raise UnauthorizedError("Invalid ID token")
        
    email = user_info.get("email")
    name = user_info.get("name", "Google User")
    
    if not email:
        raise UnauthorizedError("Google account has no email associated")
        
    user = get_user_by_email(db, email)
    if not user:
        # Create new user with random unusable password
        user = User(
            name=name,
            email=email,
            hashed_password=hash_password(secrets.token_hex(32)),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    if not user.is_active:
        raise UnauthorizedError(messages.ACCOUNT_DISABLED)
        
    return TokenResponse(
        name=user.name,
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
