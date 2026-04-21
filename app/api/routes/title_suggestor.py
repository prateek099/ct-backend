"""Route: POST /title-suggestor — generates 10 title variations for a video."""
from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from typing import List, Optional

from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.core.database import get_db
from app.core.exceptions import AppError, BadRequestError
from app.models.user import User
from app.prompts import title as title_prompt
from app.schemas.ai import ChannelContext
from app.services.llm_tracker import track_openai_call

router = APIRouter()


# ── Pydantic models ────────────────────────────────────────────────────────────

class TitleRequest(BaseModel):
    topic: str = Field(..., description="Original idea title / topic")
    hook: str = Field("", description="Opening hook line from idea")
    angle: str = Field("", description="Content angle (e.g. Beginner, Controversial)")
    format: str = Field("", description="Video format (e.g. Tutorial, Listicle)")
    script_summary: Optional[str] = Field(
        None, description="Brief summary of script content (section names)"
    )
    channel_context: Optional[ChannelContext] = None


class TitleItem(BaseModel):
    title: str
    style: str
    ctr_angle: str
    search_intent: str
    seo_keywords: List[str]
    reasoning: str


class TitleResponse(BaseModel):
    topic: str
    titles: List[TitleItem]


# ── endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/title-suggestor",
    tags=["ai-tools"],
    response_model=TitleResponse,
    summary="Generate 10 video title suggestions",
    description=(
        "Generates 10 YouTube title variations across different styles "
        "(listicle, how-to, curiosity gap, etc.) with CTR angle, "
        "search intent, SEO keywords, and reasoning for each."
    ),
    responses={
        400: {"description": "Topic cannot be empty"},
        500: {"description": "Model generation failed"},
    },
)
def generate_titles(
    request: TitleRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> TitleResponse:
    if not request.topic.strip():
        raise BadRequestError("Topic cannot be empty")

    logger.info("Title suggestor", topic=request.topic[:60])
    system_prompt, user_prompt = title_prompt.build(request)
    output = track_openai_call(
        db, user=user, endpoint="title_suggestor",
        user_prompt=user_prompt, system_prompt=system_prompt,
    )

    if "error" in output:
        raise AppError(output["error"])

    titles = output.get("titles", [])
    if not titles:
        raise AppError("Model returned no titles")

    return TitleResponse(topic=request.topic, titles=titles)
