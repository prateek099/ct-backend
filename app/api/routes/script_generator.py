"""Route: POST /script-generator — generates a full YouTube video script."""
from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.core.database import get_db
from app.core.exceptions import AppError, BadRequestError
from app.models.user import User
from app.prompts import script as script_prompt
from app.schemas.ai import ChannelContext
from app.services import prompt_override_service
from app.services.llm_tracker import track_openai_call

router = APIRouter()


# ── Pydantic models ────────────────────────────────────────────────────────────

class ScriptRequest(BaseModel):
    title: str = Field(..., description="Video title (from idea generator)")
    hook: str = Field(..., description="Opening hook line")
    angle: str = Field(..., description="Content angle (e.g. Beginner, Controversial)")
    format: str = Field(..., description="Video format (e.g. Tutorial, Listicle)")
    reasoning: Optional[str] = Field(
        None,
        description="Why-this-works reasoning for the idea. Used to infer mood when flavor='auto'.",
    )
    flavor: str = Field(
        "auto",
        description="Script tone: auto | educational | entertaining | storytelling | documentary. 'auto' lets the LLM infer mood from title+hook+angle+reasoning.",
    )
    # Prateek: Steering fields — all optional; applied on top of the base flavor prompt.
    tone: Optional[str] = Field(
        None,
        description="Explicit tone override (e.g. Casual, Professional, Funny, Dramatic, Urgent).",
    )
    audience: Optional[str] = Field(
        None,
        description="Target audience free text (e.g. 'beginner Python developers').",
    )
    length: Optional[Literal["short", "medium", "long"]] = Field(
        None,
        description="Target script length: short (~3 min) | medium (~7 min) | long (~15 min).",
    )
    pov_structure: Optional[Literal["first_person_story", "narrator_tutorial", "listicle", "review"]] = Field(
        None,
        description="Narrative structure / point-of-view style.",
    )
    channel_context: Optional[ChannelContext] = None


class ScriptSection(BaseModel):
    name: str
    content: str


class ScriptData(BaseModel):
    word_count: int
    estimated_duration_seconds: int
    sections: List[ScriptSection]
    full_script: str


class ScriptResponse(BaseModel):
    title: str
    flavor: str
    script: ScriptData


# ── endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/script-generator",
    tags=["ai-tools"],
    response_model=ScriptResponse,
    summary="Generate a video script",
    description=(
        "Generates a full, section-by-section YouTube script calibrated to the "
        "channel's average video duration. Flavor can be 'auto' (LLM infers mood "
        "from title/hook/angle/reasoning) or one of: educational, entertaining, "
        "storytelling, documentary."
    ),
    responses={
        400: {"description": "Missing or invalid input"},
        500: {"description": "Model generation failed"},
    },
)
def generate_script(
    request: ScriptRequest,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> ScriptResponse:
    if not request.title.strip():
        raise BadRequestError("Title cannot be empty")

    logger.info("Script gen", title=request.title[:60], flavor=request.flavor)
    override = prompt_override_service.get_override(db, "script")
    system_prompt, user_prompt = script_prompt.build(
        request,
        system_override=override.system_prompt if override else None,
        template_override=override.user_prompt_template if override else None,
    )
    output = track_openai_call(
        db, user=user, endpoint="script_generator",
        user_prompt=user_prompt, system_prompt=system_prompt,
    )

    if "error" in output:
        raise AppError(output["error"])

    sections = output.get("sections", [])
    if not sections:
        raise AppError("Model returned no script sections")

    return ScriptResponse(
        title=request.title,
        flavor=request.flavor,
        script=ScriptData(
            word_count=output.get("word_count", 0),
            estimated_duration_seconds=output.get("estimated_duration_seconds", 0),
            sections=sections,
            full_script=output.get("full_script", ""),
        ),
    )
