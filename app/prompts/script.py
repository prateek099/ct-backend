"""Prompt templates for the /script-generator endpoint."""
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.api.routes.script_generator import ScriptRequest

# Prateek: ~130 words per minute is average speaking pace for YouTube videos
WORDS_PER_MINUTE = 130

LENGTH_TARGETS = {
    "short":  3,   # minutes
    "medium": 7,
    "long":  15,
}

FLAVORS = {
    "educational": "structured, clear, step-by-step — teach the viewer something actionable",
    "entertaining": "energetic, casual, humour-driven — keep the viewer engaged and smiling",
    "storytelling": "narrative arc with personal anecdotes — build emotional connection",
    "documentary": "research-heavy, authoritative, journalistic — present facts and evidence",
}

POV_DESCRIPTIONS = {
    "first_person_story": "told in first person as a personal experience/story",
    "narrator_tutorial":  "third-person narrator walking the viewer through steps",
    "listicle":           "numbered-list structure (e.g. '5 ways to…')",
    "review":             "structured product/topic review with pros, cons, verdict",
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
{steering_block}
TARGET LENGTH:
  Aim for approximately {target_words} words total ({target_min} minutes; \
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


def _steering_block(req: "ScriptRequest") -> str:
    """Build the optional steering lines injected between DETAILS and TARGET LENGTH."""
    lines = []
    if req.tone:
        lines.append(f"  Tone    : {req.tone}")
    if req.audience:
        lines.append(f"  Audience: {req.audience}")
    if req.pov_structure:
        lines.append(f"  POV     : {POV_DESCRIPTIONS.get(req.pov_structure, req.pov_structure)}")
    return ("\n" + "\n".join(lines) + "\n") if lines else ""


def build(
    req: "ScriptRequest",
    system_override: Optional[str] = None,
    template_override: Optional[str] = None,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the script-gen call."""
    # Prateek: length steering overrides channel average; fall back to channel avg then 10 min.
    if req.length and req.length in LENGTH_TARGETS:
        target_min = LENGTH_TARGETS[req.length]
    else:
        avg_duration = req.channel_context.average_duration_seconds if req.channel_context else 600
        target_min = max(1, avg_duration // 60)

    target_words = target_min * WORDS_PER_MINUTE

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

    template = template_override or USER_PROMPT_TEMPLATE
    user_prompt = template.format(
        title=req.title,
        hook=req.hook,
        angle=req.angle,
        format=req.format,
        flavor=flavor.capitalize(),
        flavor_desc=flavor_desc,
        steering_block=_steering_block(req),
        target_words=target_words,
        target_min=target_min,
        wpm=WORDS_PER_MINUTE,
        channel_block=channel_block,
    )
    return system_override or SYSTEM_PROMPT, user_prompt
