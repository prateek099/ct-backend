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
            logger.error("OPENAI_API_KEY is not configured — set it in .env")
            raise AppError("Internal server error")
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


def openai_call(
    user_prompt: str,
    system_prompt: str = "You are a JSON API. Return only valid JSON with no extra text.",
    model: str = DEFAULT_MODEL,
) -> tuple[dict, dict, str]:
    """
    Low-level OpenAI call — returns (parsed_dict, usage_dict, raw_response_text).

    usage_dict keys: prompt_tokens, completion_tokens, total_tokens (int | None each).
    Use this when you need token counts (e.g. the LLM tracker).

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
        raw_text = response.choices[0].message.content or ""
        usage = response.usage
        usage_dict = {
            "prompt_tokens": usage.prompt_tokens if usage else None,
            "completion_tokens": usage.completion_tokens if usage else None,
            "total_tokens": usage.total_tokens if usage else None,
        }
        return extract_json(raw_text), usage_dict, raw_text
    except (BadRequestError, AppError):
        raise
    except Exception as e:
        logger.exception("OpenAI API error")
        raise AppError(str(e))


def openai_wrapper(
    user_prompt: str,
    system_prompt: str = "You are a JSON API. Return only valid JSON with no extra text.",
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Convenience wrapper — returns only the parsed JSON dict.
    Delegates to openai_call(); use openai_call() directly when token usage is needed.
    """
    result, _, _ = openai_call(user_prompt, system_prompt, model)
    return result
