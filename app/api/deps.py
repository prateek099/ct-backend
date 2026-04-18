from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate the JWT from the Authorization header.
    Returns the authenticated User or raises UnauthorizedError.
    """
    if not credentials:
        raise UnauthorizedError("Authorization header missing.")

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise UnauthorizedError("Token is invalid or expired.")

    if payload.get("type") != "access":
        raise UnauthorizedError("Token is not an access token.")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise UnauthorizedError("User not found.")
    if not user.is_active:
        raise ForbiddenError("Account is disabled.")
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Alias — ensures user is active (already checked in get_current_user)."""
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Requires a valid bearer token (401 if missing or invalid).
    Returns the User for real tokens; returns None for demo tokens (sub='demo').
    Use on AI routes that need auth but also want to track which user called them.
    """
    if not credentials:
        raise UnauthorizedError("Authorization header missing.")

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise UnauthorizedError("Token is invalid or expired.")

    if payload.get("type") != "access":
        raise UnauthorizedError("Token is not an access token.")

    # Prateek: Demo tokens carry sub='demo' — no DB user exists for them.
    if payload.get("sub") == "demo":
        return None

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise UnauthorizedError("User not found.")
    if not user.is_active:
        raise ForbiddenError("Account is disabled.")
    return user


def require_valid_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    Validate JWT signature and type only — no DB lookup.
    Works for demo tokens (sub='demo') and real user tokens alike.
    Use this dependency on AI/YouTube routes that don't need a User object.
    """
    if not credentials:
        raise UnauthorizedError("Authorization header missing.")

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise UnauthorizedError("Token is invalid or expired.")

    if payload.get("type") != "access":
        raise UnauthorizedError("Token is not an access token.")

    return payload
