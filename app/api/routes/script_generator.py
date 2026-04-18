from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from typing import List, Optional

from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.core.database import get_db
from app.core.exceptions import AppError, BadRequestError
from app.models.user import User
from app.services.llm_tracker import track_openai_call

router = APIRouter()

# Prateek: ~130 words per minute is average speaking pace for YouTube videos
WORDS_PER_MINUTE = 130

FLAVORS = {
    "educational": "structured, clear, step-by-step — teach the viewer something actionable",
    "entertaining": "energetic, casual, humour-driven — keep the viewer engaged and smiling",
    "storytelling": "narrative arc with personal anecdotes — build emotional connection",
    "documentary": "research-heavy, authoritative, journalistic — present facts and evidence",
}

SYSTEM_PROMPT = (
    "You are a professional YouTube scriptwriter. "
    "You always respond with valid JSON only — no markdown, no extra text."
)

USER_PROMPT_TEMPLATE = """\
Write a complete, ready-to-record YouTube video script.

VIDEO DETAILS:
  Title   : {title}
  Hook    : {hook}
  Angle   : {angle}
  Format  : {format}
  Flavor  : {flavor} — {flavor_desc}

TARGET LENGTH:
  Aim for approximately {target_words} words total (channel average is {avg_min} minutes; \
speaking pace ≈ {wpm} words/min).

{channel_block}

SCRIPT REQUIREMENTS:
  - Start with the hook word-for-word as the very first spoken line
  - Include natural transitions between sections
  - Add [B-ROLL: description] notes where relevant
  - End with a clear Call-to-Action (like, subscribe, comment prompt)
  - Write as if speaking directly to camera — conversational, not academic

Return JSON with this exact structure:
{{
  "word_count": <integer>,
  "estimated_duration_seconds": <integer>,
  "sections": [
    {{"name": "Hook / Intro", "content": "<spoken text>"}},
    {{"name": "Section title", "content": "<spoken text>"}},
    ...more sections...,
    {{"name": "Outro / CTA", "content": "<spoken text>"}}
  ],
  "full_script": "<complete script as a single string with section headings>"
}}
No extra keys outside the root object.\
"""

CHANNEL_BLOCK_TEMPLATE = """\
CHANNEL CONTEXT:
  Channel : {channel_name}
  Niche   : inferred from recent titles below
  Recent titles:
{titles}

Match the tone and vocabulary style of this channel.\
"""


def _build_prompts(req: "ScriptRequest") -> tuple[str, str]:
    avg_duration = req.channel_context.average_duration_seconds if req.channel_context else 600
    avg_min = max(1, avg_duration // 60)
    target_words = avg_min * WORDS_PER_MINUTE

    channel_block = ""
    if req.channel_context and req.channel_context.recent_video_titles:
        titles = "\n".join(
            f"    - {t}" for t in req.channel_context.recent_video_titles[:10]
        )
        channel_block = CHANNEL_BLOCK_TEMPLATE.format(
            channel_name=req.channel_context.channel_name,
            titles=titles,
        )

    flavor = req.flavor.lower() if req.flavor else "educational"
    flavor_desc = FLAVORS.get(flavor, FLAVORS["educational"])

    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=req.title,
        hook=req.hook,
        angle=req.angle,
        format=req.format,
        flavor=flavor.capitalize(),
        flavor_desc=flavor_desc,
        target_words=target_words,
        avg_min=avg_min,
        wpm=WORDS_PER_MINUTE,
        channel_block=channel_block,
    )
    return SYSTEM_PROMPT, user_prompt


# ── Pydantic models ────────────────────────────────────────────────────────────

class ScriptChannelContext(BaseModel):
    channel_name: str = ""
    average_duration_seconds: int = 600
    recent_video_titles: List[str] = []


class ScriptRequest(BaseModel):
    title: str = Field(..., description="Video title (from idea generator)")
    hook: str = Field(..., description="Opening hook line")
    angle: str = Field(..., description="Content angle (e.g. Beginner, Controversial)")
    format: str = Field(..., description="Video format (e.g. Tutorial, Listicle)")
    flavor: str = Field(
        "educational",
        description="Script tone: educational | entertaining | storytelling | documentary",
    )
    channel_context: Optional[ScriptChannelContext] = None


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
        "channel's average video duration. Supports four flavors: educational, "
        "entertaining, storytelling, and documentary."
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
    system_prompt, user_prompt = _build_prompts(request)
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
