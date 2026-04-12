import json

from openai import OpenAI
from loguru import logger

from app.core.config import settings
from app.core.exceptions import AppError, BadRequestError

DEFAULT_MODEL = "gpt-4o-mini"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Return a cached OpenAI client (avoids re-creating per request)."""
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise AppError("OPENAI_API_KEY is not configured")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def extract_json(content: str) -> dict:
    """Parse JSON from model output, stripping markdown fences if present."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Prateek: Drop first line (```json) and last line (```)
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    try:
        return json.loads(text)
    except Exception:
        return {
            "raw_response": content,
            "error": "Could not parse JSON — model returned unexpected format",
        }


def openai_wrapper(
    user_prompt: str,
    system_prompt: str = "You are a JSON API. Return only valid JSON with no extra text.",
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Call OpenAI Chat Completions API and return a parsed JSON dict.

    Args:
        user_prompt:   The user-facing instruction / content.
        system_prompt: System-level behaviour instructions.
        model:         Model to use (defaults to DEFAULT_MODEL).

    Returns:
        Parsed JSON dict, or an error dict if parsing fails.

    Raises:
        BadRequestError 400 if prompt is empty.
        AppError 500 on API / network errors.
    """
    if not user_prompt.strip():
        raise BadRequestError("Prompt cannot be empty")

    client = _get_client()
    logger.info("OpenAI request", model=model, prompt_len=len(user_prompt))
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        return extract_json(content)
    except (BadRequestError, AppError):
        raise
    except Exception as e:
        logger.exception("OpenAI API error")
        raise AppError(str(e))
