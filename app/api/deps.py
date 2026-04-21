"""FastAPI dependencies — get_current_user, get_optional_user, require_admin, ownership helper."""
from typing import Type, TypeVar

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_token
from app.models.user import User

T = TypeVar("T")

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


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires the caller to be an admin user.
    Use on routes that should be admin-only (e.g. prompt management, user list).
    """
    if not current_user.is_admin:
        raise ForbiddenError("Admin privileges required.")
    return current_user


def get_owned_or_404(
    db: Session,
    model: Type[T],
    resource_id: int,
    user: User,
    user_id_attr: str = "user_id",
) -> T:
    """
    Fetch a row by id, enforcing that it belongs to `user`.
    Raises NotFoundError (not Forbidden) so existence of another user's
    resource does not leak. Use across all owned-resource services.
    """
    row = db.query(model).filter(model.id == resource_id).first()
    if row is None or getattr(row, user_id_attr) != user.id:
        raise NotFoundError(f"{model.__name__} not found.")
    return row


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
