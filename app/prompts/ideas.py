"""Prompt templates for the /video-idea-gen endpoint."""
from typing import Optional

from app.schemas.ai import ChannelContext

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


def build(
    topic: str,
    channel_context: Optional[ChannelContext],
    system_override: Optional[str] = None,
    template_override: Optional[str] = None,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the idea-gen call.

    Admin overrides (from the DB) can replace either constant. If the template
    is overridden it must keep the {channel_block} and {topic} placeholders.
    """
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

    template = template_override or USER_PROMPT_TEMPLATE
    user_prompt = template.format(channel_block=channel_block, topic=topic)
    return system_override or SYSTEM_PROMPT, user_prompt
