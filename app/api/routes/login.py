import base64

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import create_access_token, create_refresh_token
from app.schemas.auth import TokenResponse

router = APIRouter()

# Prateek: Hardcoded demo credentials — base64-encoded on the wire
HARDCODED_USERNAME = "u"
HARDCODED_PASSWORD = "p"


class WorkflowLoginRequest(BaseModel):
    username: str = Field(..., description="Base64-encoded username", examples=["dQ=="])
    password: str = Field(..., description="Base64-encoded password", examples=["cA=="])


@router.post(
    "/login",
    tags=["auth"],
    response_model=TokenResponse,
    summary="Demo login (base64-encoded credentials)",
    description=(
        "Validates base64-encoded username/password against demo hardcoded credentials. "
        "Returns a JWT token pair (access + refresh) with sub='demo'. "
        "Use the access token as Bearer on all AI/YouTube endpoints."
    ),
    responses={
        400: {"description": "Invalid base64 encoding"},
        401: {"description": "Invalid credentials"},
    },
)
async def workflow_login(request: WorkflowLoginRequest) -> TokenResponse:
    try:
        decoded_username = base64.b64decode(request.username).decode("utf-8")
        decoded_password = base64.b64decode(request.password).decode("utf-8")
    except Exception:
        raise BadRequestError("Invalid base64 encoding")

    if decoded_username != HARDCODED_USERNAME or decoded_password != HARDCODED_PASSWORD:
        # Prateek: Log first 10 chars only — never log full credentials
        logger.warning("Demo login failed", username=decoded_username[:10])
        raise UnauthorizedError("Invalid credentials")

    logger.info("Demo login successful")
    return TokenResponse(
        access_token=create_access_token("demo"),
        refresh_token=create_refresh_token("demo"),
    )
