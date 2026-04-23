"""Route: POST /video-idea-gen — generates video ideas from a topic or niche."""
from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from typing import Any, Dict, Literal, Optional

from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.core.database import get_db
from app.core.exceptions import AppError, BadRequestError
from app.models.user import User
from app.prompts import ideas as ideas_prompt
from app.schemas.ai import ChannelContext
from app.services import prompt_override_service
from app.services.llm_tracker import track_openai_call

router = APIRouter()


# ── Pydantic models ────────────────────────────────────────────────────────────

class VideoIdeaRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="Topic or niche to generate video ideas for.",
        examples=["Fitness tips for busy professionals"],
    )
    # Prateek: "channel" = prompt came from a YT URL/@handle (channel context likely present);
    # "niche" = free-text niche (no channel lookup performed).
    input_type: Literal["channel", "niche"] = Field(
        default="channel",
        description="Whether the prompt is a channel identifier or a free-text niche.",
    )
    count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of ideas to generate.",
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

    logger.info("Video idea gen", topic=request.prompt[:50], input_type=request.input_type, count=request.count)
    override = prompt_override_service.get_override(db, "ideas")
    system_prompt, user_prompt = ideas_prompt.build(
        request.prompt,
        request.channel_context,
        input_type=request.input_type,
        count=request.count,
        system_override=override.system_prompt if override else None,
        template_override=override.user_prompt_template if override else None,
    )
    output = track_openai_call(
        db, user=user, endpoint="video_idea_gen",
        user_prompt=user_prompt, system_prompt=system_prompt,
    )

    if isinstance(output, dict) and "error" in output:
        raise AppError(output["error"])

    return VideoIdeaResponse(prompt=request.prompt, response=output)
