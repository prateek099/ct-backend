"""Route: POST /video-idea-gen — generates 10 video ideas from a topic."""
from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.core.database import get_db
from app.core.exceptions import AppError, BadRequestError
from app.models.user import User
from app.prompts import ideas as ideas_prompt
from app.schemas.ai import ChannelContext
from app.services.llm_tracker import track_openai_call

router = APIRouter()


# ── Pydantic models ────────────────────────────────────────────────────────────

class VideoIdeaRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="Topic or niche to generate video ideas for.",
        examples=["Fitness tips for busy professionals"],
    )
    channel_context: Optional[ChannelContext] = Field(
        None,
        description="Optional YouTube channel data to personalise ideas.",
    )


class VideoIdeaResponse(BaseModel):
    prompt: str
    response: Dict[str, Any]


# ── endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/video-idea-gen",
    tags=["ai-tools"],
    response_model=VideoIdeaResponse,
    summary="Generate video ideas",
    description=(
        "Generates 10 structured video ideas using OpenAI. "
        "Optionally accepts YouTube channel context for personalised, channel-aware suggestions."
    ),
    responses={
        400: {"description": "Prompt cannot be empty"},
        500: {"description": "Model generation failed"},
    },
)
def generate_video_ideas(
    request: VideoIdeaRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> VideoIdeaResponse:
    if not request.prompt.strip():
        raise BadRequestError("Prompt cannot be empty")

    logger.info("Video idea gen", topic=request.prompt[:50])
    system_prompt, user_prompt = ideas_prompt.build(request.prompt, request.channel_context)
    output = track_openai_call(
        db, user=user, endpoint="video_idea_gen",
        user_prompt=user_prompt, system_prompt=system_prompt,
    )

    if isinstance(output, dict) and "error" in output:
        raise AppError(output["error"])

    return VideoIdeaResponse(prompt=request.prompt, response=output)
