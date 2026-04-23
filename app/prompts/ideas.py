"""Prompt templates for the /video-idea-gen endpoint."""
from typing import Optional

from app.schemas.ai import ChannelContext

SYSTEM_PROMPT = (
    "You are an expert YouTube content strategist. "
    "You always respond with valid JSON only — no markdown, no extra text."
)

USER_PROMPT_TEMPLATE = """\
Generate exactly {count} high-potential video ideas for the topic/niche below.
{channel_block}
{niche_block}TOPIC / NICHE: {topic}

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
Return exactly {count} items. No extra keys outside the root object.\
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

# Prateek: Niche mode — user typed free text instead of a YT URL.
# Reinforce that the niche IS the creative brief, not a channel constraint.
NICHE_BLOCK = """\
MODE: Niche-first (no specific channel — optimise for the niche broadly).
  - Ideas should appeal to a wide audience within this niche
  - Prioritise search intent and trending sub-topics over channel history
"""


def build(
    topic: str,
    channel_context: Optional[ChannelContext],
    input_type: str = "channel",
    count: int = 5,
    system_override: Optional[str] = None,
    template_override: Optional[str] = None,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the idea-gen call."""
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

    niche_block = NICHE_BLOCK if input_type == "niche" else ""

    template = template_override or USER_PROMPT_TEMPLATE
    user_prompt = template.format(
        channel_block=channel_block,
        niche_block=niche_block,
        topic=topic,
        count=count,
    )
    return system_override or SYSTEM_PROMPT, user_prompt
