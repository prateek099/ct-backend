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
from loguru import logger
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.user_service import get_user_by_email
from app.services.email_service import send_welcome_email


def register(db: Session, payload: RegisterRequest) -> User:
    if get_user_by_email(db, payload.email):
        logger.warning("Registration failed: Email already exists", email=payload.email)
        raise ConflictError(messages.EMAIL_ALREADY_REGISTERED)
    
    logger.info("Creating new user via normal signup", email=payload.email, name=payload.name)
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        logger.success("User successfully stored in database", user_id=user.id, email=user.email)
    except Exception as e:
        db.rollback()
        logger.error("Failed to store user in database", error=str(e))
        raise

    # Send welcome email (non-blocking, won't break signup if it fails)
    try:
        send_welcome_email(user.email, user.name)
    except Exception as e:
        logger.error("Welcome email dispatch failed", email=user.email, error=str(e))
    return user


def login(db: Session, payload: LoginRequest) -> TokenResponse:
    logger.info("Login attempt", email=payload.email)
    user = get_user_by_email(db, payload.email)
    if not user:
        logger.warning("Login failed: User not found", email=payload.email)
        raise UnauthorizedError(messages.INVALID_CREDENTIALS)
        
    if not verify_password(payload.password, user.hashed_password):
        logger.warning("Login failed: Incorrect password", email=payload.email)
        raise UnauthorizedError(messages.INVALID_CREDENTIALS)
        
    if not user.is_active:
        logger.warning("Login failed: Account disabled", email=payload.email)
        raise UnauthorizedError(messages.ACCOUNT_DISABLED)
        
    logger.success("Login successful", user_id=user.id, email=user.email)
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
    
    logger.info("Google OAuth login attempt")
    response = httpx.post(token_url, data=data)
    if response.status_code != 200:
        logger.error(f"Google Token API failed: {response.text}")
        raise UnauthorizedError(f"Failed to authenticate with Google: {response.text}")
        
    tokens = response.json()
    id_token = tokens.get("id_token")
    if not id_token:
        logger.error("No ID token received from Google")
        raise UnauthorizedError("No ID token received from Google")
            
    # Decode ID token to get user info
    try:
        user_info = jwt.get_unverified_claims(id_token)
    except Exception:
        logger.error("Failed to decode Google ID token")
        raise UnauthorizedError("Invalid ID token")
        
    email = user_info.get("email")
    name = user_info.get("name", "Google User")
    
    if not email:
        logger.error("Google account has no email")
        raise UnauthorizedError("Google account has no email associated")
        
    user = get_user_by_email(db, email)
    if not user:
        logger.info("User not found for Google email, creating new record", email=email)
        # Create new user with random unusable password
        user = User(
            name=name,
            email=email,
            hashed_password=hash_password(secrets.token_hex(32)),
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
            logger.success("New Google user stored in database", user_id=user.id, email=user.email)
        except Exception as e:
            db.rollback()
            logger.error("Failed to store Google user", error=str(e))
            raise

        # Send welcome email (non-blocking, won't break signup if it fails)
        try:
            send_welcome_email(user.email, user.name)
        except Exception as e:
            logger.error("Welcome email dispatch failed", email=user.email, error=str(e))
    else:
        logger.info("Existing user logged in via Google", user_id=user.id, email=email)
        
    if not user.is_active:
        logger.warning("Google login failed: Account disabled", email=email)
        raise UnauthorizedError(messages.ACCOUNT_DISABLED)
        
    return TokenResponse(
        name=user.name,
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
