"""Password hashing (bcrypt) and JWT encode/decode helpers."""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings

# ── Password hashing (direct bcrypt — compatible with bcrypt 4.x and 5.x) ────

def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT ───────────────────────────────────────────────────────────────────────

def _create_token(subject: Any, expires_delta: timedelta, token_type: str) -> str:
    expire = int((datetime.now(timezone.utc) + expires_delta).timestamp())
    iat = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": iat,
        "type": token_type,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: Any) -> str:
    """Create a short-lived access token (default 30 min)."""
    return _create_token(
        subject,
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
        token_type="access",
    )


def create_refresh_token(subject: Any) -> str:
    """Create a long-lived refresh token (default 7 days)."""
    return _create_token(
        subject,
        timedelta(days=settings.jwt_refresh_token_expire_days),
        token_type="refresh",
    )


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.
    Raises jose.JWTError on invalid / expired tokens.
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


def create_password_reset_token(email: str) -> str:
    """Create a short-lived token for password reset (15 min)."""
    return _create_token(
        email,
        timedelta(minutes=15),
        token_type="password_reset",
    )
