"""Route: POST /seo-description — generates SEO description, hashtags, and tags."""
from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from typing import List, Optional

from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.core.database import get_db
from app.core.exceptions import AppError, BadRequestError
from app.models.user import User
from app.prompts import seo as seo_prompt
from app.prompts.seo import HASHTAG_COUNT, MAX_TAGS_CHARS
from app.schemas.ai import ChannelContext
from app.services import prompt_override_service
from app.services.llm_tracker import track_openai_call

router = APIRouter()


# ── Pydantic models ────────────────────────────────────────────────────────────

class SeoRequest(BaseModel):
    title: str = Field(..., description="Final selected video title")
    topic: str = Field(..., description="Original idea topic / niche")
    script_outline: Optional[str] = Field(
        None,
        description="Section names joined with ' → ' (from script generator)",
    )
    niche: Optional[str] = Field(
        None,
        description="Channel niche override. Inferred from channel context if omitted.",
    )
    channel_context: Optional[ChannelContext] = None


class SeoResponse(BaseModel):
    title: str
    description: str
    description_word_count: int
    hashtags: List[str]
    tags: str
    tags_char_count: int
    primary_keyword: str
    secondary_keywords: List[str]


# ── endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/seo-description",
    tags=["ai-tools"],
    response_model=SeoResponse,
    summary="Generate SEO description, hashtags, and tags",
    description=(
        "Generates an SEO-optimised YouTube video description (< 2000 words) "
        "with chapters, CTA, and social links placeholders, "
        f"plus {HASHTAG_COUNT} hashtags at the end and a comma-separated tags "
        f"string under {MAX_TAGS_CHARS} characters."
    ),
    responses={
        400: {"description": "Title or topic cannot be empty"},
        500: {"description": "Model generation failed"},
    },
)
def generate_seo_description(
    request: SeoRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> SeoResponse:
    if not request.title.strip():
        raise BadRequestError("Title cannot be empty")
    if not request.topic.strip():
        raise BadRequestError("Topic cannot be empty")

    logger.info("SEO description gen", title=request.title[:60])
    override = prompt_override_service.get_override(db, "seo")
    system_prompt, user_prompt = seo_prompt.build(
        request,
        system_override=override.system_prompt if override else None,
        template_override=override.user_prompt_template if override else None,
    )
    output = track_openai_call(
        db, user=user, endpoint="seo_description",
        user_prompt=user_prompt, system_prompt=system_prompt,
    )

    if "error" in output:
        raise AppError(output["error"])

    description = output.get("description", "")
    if not description:
        raise AppError("Model returned empty description")

    # Prateek: Enforce tags char limit — trim trailing entries rather than erroring
    tags_str = output.get("tags", "")
    if len(tags_str) > MAX_TAGS_CHARS:
        parts = [t.strip() for t in tags_str.split(",")]
        trimmed = []
        running = 0
        for part in parts:
            if running + len(part) + 2 > MAX_TAGS_CHARS:
                break
            trimmed.append(part)
            running += len(part) + 2
        tags_str = ", ".join(trimmed)

    return SeoResponse(
        title=request.title,
        description=description,
        description_word_count=output.get("description_word_count", len(description.split())),
        hashtags=output.get("hashtags", [])[:HASHTAG_COUNT],
        tags=tags_str,
        tags_char_count=len(tags_str),
        primary_keyword=output.get("primary_keyword", ""),
        secondary_keywords=output.get("secondary_keywords", []),
    )
