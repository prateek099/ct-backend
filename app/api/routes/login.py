"""Route: POST /login — demo login that checks base64 creds against settings."""
import base64

from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core import messages
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppError, UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.schemas.auth import TokenResponse
from app.services.user_service import get_user_by_email

router = APIRouter()


class WorkflowLoginRequest(BaseModel):
    username: str = Field(
        ...,
        description="Base64-encoded username (demo: 'u') or registered email",
        examples=["dQ=="],
    )
    password: str = Field(
        ...,
        description="Base64-encoded password (demo: 'p')",
        examples=["cA=="],
    )


@router.post(
    "/login",
    tags=["auth"],
    response_model=TokenResponse,
    summary="Workflow login (base64-encoded credentials)",
    description=(
        "Validates base64-encoded username/password. "
        "Checks hardcoded demo credentials first (username='u', password='p'), "
        "then falls back to database lookup using username as email. "
        "Returns a JWT token pair (access + refresh). "
        "Use the access token as Bearer on all AI/YouTube endpoints."
    ),
    responses={
        401: {"description": "Invalid credentials"},
    },
)
async def workflow_login(
    request: WorkflowLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        # Prateek: Decode base64 — log real error details but never surface them to the client.
        try:
            decoded_username = base64.b64decode(request.username).decode("utf-8")
            decoded_password = base64.b64decode(request.password).decode("utf-8")
            # decoded_username = request.username
            # decoded_password = request.password
        except Exception as exc:
            logger.error("Failed to decode base64 credentials", error=str(exc))
            raise UnauthorizedError(messages.INVALID_CREDENTIALS)

        # Prateek: Hardcoded demo credentials take priority — no DB hit needed.
        if decoded_username == settings.demo_username and decoded_password == settings.demo_password:
            logger.info("Demo login successful")
            return TokenResponse(
                name="Creator",
                access_token=create_access_token("demo"),
                refresh_token=create_refresh_token("demo"),
            )

        # Prateek: Fall back to DB — treat decoded_username as email.
        user = get_user_by_email(db, decoded_username)
        if not user or not verify_password(decoded_password, user.hashed_password):
            logger.warning(
                "Workflow login failed — invalid credentials",
                username=decoded_username[:10],
            )
            raise UnauthorizedError(messages.INVALID_CREDENTIALS)

        if not user.is_active:
            logger.warning("Workflow login failed — account disabled", user_id=user.id)
            raise UnauthorizedError(messages.INVALID_CREDENTIALS)

        logger.info("Workflow login successful", user_id=user.id)
        return TokenResponse(
            name=user.name,
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    except AppError:
        # Prateek: Re-raise all AppErrors (401 etc.) unchanged.
        raise
    except Exception as exc:
        # Prateek: Unexpected system error (e.g. DB down) — log and surface as 500.
        logger.error("Unexpected error during workflow login", error=str(exc))
        raise
