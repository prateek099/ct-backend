"""Prompt templates for the /title-suggestor endpoint."""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.api.routes.title_suggestor import TitleRequest

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


def build(
    req: "TitleRequest",
    system_override: Optional[str] = None,
    template_override: Optional[str] = None,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the title-gen call."""
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

    template = template_override or USER_PROMPT_TEMPLATE
    user_prompt = template.format(
        topic=req.topic,
        hook=req.hook,
        angle=req.angle,
        format=req.format,
        script_block=script_block,
        channel_block=channel_block,
        year=year,
    )
    return system_override or SYSTEM_PROMPT, user_prompt
