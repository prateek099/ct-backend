from datetime import datetime
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

# ── Prompts ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert YouTube title strategist with deep knowledge of CTR optimisation, "
    "search intent, and audience psychology. "
    "You always respond with valid JSON only — no markdown, no extra text."
)

USER_PROMPT_TEMPLATE = """\
Generate exactly 10 high-performing YouTube video title variations.

VIDEO DETAILS:
  Original idea title : {topic}
  Hook                : {hook}
  Angle               : {angle}
  Format              : {format}
{script_block}
{channel_block}

TITLE VARIETY REQUIREMENTS:
  Produce one title in each of these styles:
  1. Numbered listicle      (e.g. "7 Ways to…")
  2. How-to / Tutorial      (e.g. "How to… Without…")
  3. Question               (e.g. "Why Does… ?")
  4. Curiosity gap          (e.g. "The Real Reason…", "Nobody Talks About…")
  5. Controversy / Pattern-break (e.g. "Stop Doing X — Here's Why")
  6. Personal result        (e.g. "I Tried X for 30 Days — Here's What Happened")
  7. Comparison             (e.g. "X vs Y: Which Is Actually Better?")
  8. Ultimate / Authority   (e.g. "The Complete Guide to…")
  9. FOMO / Urgency         (e.g. "Before You… Watch This")
  10. Trending / Timely     (e.g. "The New Way Everyone Is Doing X in {year}")

RULES:
  - Keep every title under 70 characters when possible (YouTube truncates at ~60–70)
  - Front-load the most important keyword
  - Do NOT use clickbait that misrepresents the content
  - Include the primary niche keyword naturally

Return a JSON object with this exact structure:
{{
  "titles": [
    {{
      "title": "The actual YouTube title",
      "style": "Style label from the list above",
      "ctr_angle": "Emotional/psychological hook (e.g. Curiosity, Fear, Aspiration, Social Proof)",
      "search_intent": "What a viewer typing this into search is looking for",
      "seo_keywords": ["keyword1", "keyword2"],
      "reasoning": "Why this title will perform well — specific, 1-2 sentences"
    }}
  ]
}}
Return exactly 10 title objects. No extra keys outside the root object.\
"""

SCRIPT_BLOCK_TEMPLATE = """\
  Script summary      : {script_summary}"""

CHANNEL_BLOCK_TEMPLATE = """\

CHANNEL CONTEXT:
  Name   : {channel_name}
  Handle : {handle}
  Recent titles (for tone/style reference):
{titles}
"""


def _build_prompts(req: "TitleRequest") -> tuple[str, str]:
    year = datetime.now().year

    script_block = ""
    if req.script_summary:
        script_block = SCRIPT_BLOCK_TEMPLATE.format(
            script_summary=req.script_summary[:400]
        )

    channel_block = ""
    if req.channel_context:
        titles = "\n".join(
            f"    - {t}" for t in req.channel_context.recent_video_titles[:8]
        )
        channel_block = CHANNEL_BLOCK_TEMPLATE.format(
            channel_name=req.channel_context.channel_name,
            handle=req.channel_context.handle,
            titles=titles,
        )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        topic=req.topic,
        hook=req.hook,
        angle=req.angle,
        format=req.format,
        script_block=script_block,
        channel_block=channel_block,
        year=year,
    )
    return SYSTEM_PROMPT, user_prompt


# ── Pydantic models ────────────────────────────────────────────────────────────

class TitleChannelContext(BaseModel):
    channel_name: str = ""
    handle: str = ""
    recent_video_titles: List[str] = []


class TitleRequest(BaseModel):
    topic: str = Field(..., description="Original idea title / topic")
    hook: str = Field("", description="Opening hook line from idea")
    angle: str = Field("", description="Content angle (e.g. Beginner, Controversial)")
    format: str = Field("", description="Video format (e.g. Tutorial, Listicle)")
    script_summary: Optional[str] = Field(
        None, description="Brief summary of script content (section names)"
    )
    channel_context: Optional[TitleChannelContext] = None


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
    system_prompt, user_prompt = _build_prompts(request)
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
