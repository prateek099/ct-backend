from sqlalchemy.orm import Session

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
