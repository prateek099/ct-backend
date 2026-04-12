from fastapi import APIRouter, Depends
from loguru import logger
from pydantic import BaseModel, Field
from typing import List, Optional

from app.api.deps import require_valid_token
from app.api_wrappers.open_ai import openai_wrapper
from app.core.exceptions import AppError, BadRequestError

router = APIRouter()

# ── Constraints ────────────────────────────────────────────────────────────────
MAX_DESC_WORDS = 2000   # YouTube description limit (words, not chars)
MAX_TAGS_CHARS = 500    # YouTube tags field character limit
HASHTAG_COUNT  = 5      # Number of hashtags at bottom of description

# ── Prompts ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert YouTube SEO specialist and copywriter. "
    "You write descriptions that rank well in YouTube search AND convert viewers. "
    "You always respond with valid JSON only — no markdown, no extra text."
)

USER_PROMPT_TEMPLATE = """\
Write an SEO-optimised YouTube video description for the video below.

VIDEO DETAILS:
  Title          : {title}
  Topic          : {topic}
  Script outline : {script_outline}
  Primary niche  : {niche}
{channel_block}

DESCRIPTION REQUIREMENTS:
  1. Opening paragraph (2-3 sentences): Expand on the title, hook the viewer,
     naturally include the primary keyword in the first 100 characters.
  2. Body (bullet points or short paragraphs): Cover what viewers will learn/get.
     Sprinkle secondary keywords naturally — never keyword-stuff.
  3. Timestamps section: Add a placeholder block labelled "CHAPTERS:" with 4-6
     fictional but realistic chapter entries (00:00, 01:30, etc.).
  4. Links/resources section: Add a placeholder "RESOURCES MENTIONED:" block.
  5. CTA paragraph: Ask viewers to like, comment, subscribe, and turn on notifications.
  6. Social/community links: Add a placeholder "CONNECT WITH US:" block.
  7. Hashtags: End the description with exactly {hashtag_count} hashtags on their own line.

  HARD LIMITS:
  - Total description must be UNDER {max_desc_words} words.
  - Do NOT include the hashtags in the word count.
  - Write naturally — avoid robotic SEO padding.

TAGS REQUIREMENTS:
  - Produce a comma-separated list of SEO-optimised YouTube tags.
  - Mix broad tags (high volume) and long-tail tags (high relevance).
  - Total character length of the tags string must be UNDER {max_tags_chars} characters.
  - Do NOT use # symbols in the tags list (those are for the description hashtags).

Return a JSON object with this exact structure:
{{
  "description": "<full description text including the {hashtag_count} hashtags at the end>",
  "description_word_count": <integer, words in description excluding hashtags>,
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"],
  "tags": "<comma-separated tags string>",
  "tags_char_count": <integer>,
  "primary_keyword": "<the single most important SEO keyword for this video>",
  "secondary_keywords": ["keyword1", "keyword2", "keyword3"]
}}
No extra keys outside the root object.\
"""

CHANNEL_BLOCK_TEMPLATE = """\

CHANNEL CONTEXT:
  Channel name : {channel_name}
  Handle       : {handle}
  Niche clues from recent titles:
{titles}
"""


def _build_prompts(req: "SeoRequest") -> tuple[str, str]:
    script_outline = req.script_outline or "Full script not provided — infer from title and topic."

    # Prateek: Determine niche from explicit field, channel context, or fall back to topic
    niche = req.niche or (req.channel_context.channel_name if req.channel_context else req.topic)

    channel_block = ""
    if req.channel_context and req.channel_context.recent_video_titles:
        titles = "\n".join(
            f"    - {t}" for t in req.channel_context.recent_video_titles[:8]
        )
        channel_block = CHANNEL_BLOCK_TEMPLATE.format(
            channel_name=req.channel_context.channel_name,
            handle=req.channel_context.handle,
            titles=titles,
        )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=req.title,
        topic=req.topic,
        script_outline=script_outline[:500],
        niche=niche,
        channel_block=channel_block,
        hashtag_count=HASHTAG_COUNT,
        max_desc_words=MAX_DESC_WORDS,
        max_tags_chars=MAX_TAGS_CHARS,
    )
    return SYSTEM_PROMPT, user_prompt


# ── Pydantic models ────────────────────────────────────────────────────────────

class SeoChannelContext(BaseModel):
    channel_name: str = ""
    handle: str = ""
    recent_video_titles: List[str] = []


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
    channel_context: Optional[SeoChannelContext] = None


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
    _token: dict = Depends(require_valid_token),
) -> SeoResponse:
    if not request.title.strip():
        raise BadRequestError("Title cannot be empty")
    if not request.topic.strip():
        raise BadRequestError("Topic cannot be empty")

    logger.info("SEO description gen", title=request.title[:60])
    system_prompt, user_prompt = _build_prompts(request)
    output = openai_wrapper(user_prompt, system_prompt=system_prompt)

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
