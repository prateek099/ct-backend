from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.core.database import get_db
from app.core.exceptions import AppError, BadRequestError
from app.models.user import User
from app.services.llm_tracker import track_openai_call

router = APIRouter()


# ── Pydantic models ────────────────────────────────────────────────────────────

class ChannelContext(BaseModel):
    channel_name: str
    handle: str = ""
    description: str = ""
    subscriber_count: int = 0
    average_duration_seconds: int = 0
    recent_video_titles: List[str] = []


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


# ── Prompts ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert YouTube content strategist. "
    "You always respond with valid JSON only — no markdown, no extra text."
)

USER_PROMPT_TEMPLATE = """\
Generate exactly 10 high-potential video ideas for the topic/niche below.
{channel_block}
TOPIC / NICHE: {topic}

Return a JSON object with this exact structure:
{{
  "videoIdeas": [
    {{
      "title": "Compelling, clickable video title",
      "hook": "Opening sentence that grabs attention in the first 5 seconds",
      "angle": "Unique angle or framing (e.g. Beginner, Controversial, Data-driven)",
      "format": "Video format (e.g. Tutorial, Listicle, Documentary, Challenge)",
      "reasoning": "Why this idea will perform well for this channel and audience"
    }}
  ]
}}
Return exactly 10 items. No extra keys outside the root object.\
"""

CHANNEL_BLOCK_TEMPLATE = """\
CHANNEL CONTEXT (use this to personalise ideas):
  Name        : {channel_name}
  Handle      : {handle}
  Description : {description}
  Subscribers : {subscribers:,}
  Avg duration: {avg_min} minutes
  Recent titles:
{titles}

Rules based on channel context:
  - Do NOT repeat topics already covered in recent titles
  - Match the channel tone and target audience
  - Suggest ideas that complement existing content gaps
"""


def _build_prompts(topic: str, channel_context: Optional[ChannelContext]):
    """Return (system_prompt, user_prompt) tuple."""
    channel_block = ""
    if channel_context:
        titles = "\n".join(
            f"    - {t}" for t in channel_context.recent_video_titles[:15]
        )
        channel_block = CHANNEL_BLOCK_TEMPLATE.format(
            channel_name=channel_context.channel_name,
            handle=channel_context.handle,
            description=channel_context.description[:300],
            subscribers=channel_context.subscriber_count,
            avg_min=channel_context.average_duration_seconds // 60,
            titles=titles,
        )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        channel_block=channel_block,
        topic=topic,
    )
    return SYSTEM_PROMPT, user_prompt


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
    system_prompt, user_prompt = _build_prompts(request.prompt, request.channel_context)
    output = track_openai_call(
        db, user=user, endpoint="video_idea_gen",
        user_prompt=user_prompt, system_prompt=system_prompt,
    )

    if isinstance(output, dict) and "error" in output:
        raise AppError(output["error"])

    return VideoIdeaResponse(prompt=request.prompt, response=output)
