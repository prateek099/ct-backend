"""Wraps every OpenAI call, persists an LLMUsage row, and returns parsed JSON."""
import time

from loguru import logger
from sqlalchemy.orm import Session

from app.api_wrappers.open_ai import DEFAULT_MODEL, openai_call
from app.models.llm_usage import LLMUsage
from app.models.user import User


def track_openai_call(
    db: Session,
    *,
    user: User | None,
    endpoint: str,
    user_prompt: str,
    system_prompt: str,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Call OpenAI and record one LLMUsage row to the DB.

    Args:
        db:            Active DB session.
        user:          Authenticated User, or None for demo / system calls.
        endpoint:      Logical name of the calling route (e.g. "video_idea_gen").
        user_prompt:   The user-facing prompt sent to OpenAI.
        system_prompt: The system-level prompt sent to OpenAI.
        model:         OpenAI model identifier.

    Returns:
        Parsed JSON dict from OpenAI (same shape as openai_wrapper()).

    Raises:
        Any exception from openai_call() — the DB row is still written with status="error".
    """
    username = user.name if user else "SYSTEM_USAGE"
    user_id = user.id if user else None

    t0 = time.monotonic()
    status = "success"
    error_message: str | None = None
    result: dict = {}
    usage_dict: dict = {}
    response_text: str | None = None

    try:
        result, usage_dict, response_text = openai_call(user_prompt, system_prompt, model)
    except Exception as exc:
        status = "error"
        error_message = str(exc)
        raise
    finally:
        duration_ms = int((time.monotonic() - t0) * 1000)
        _persist(
            db=db,
            user_id=user_id,
            username=username,
            endpoint=endpoint,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_text=response_text,
            usage=usage_dict,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
        )

    return result


def _persist(
    *,
    db: Session,
    user_id: int | None,
    username: str,
    endpoint: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_text: str | None,
    usage: dict,
    duration_ms: int,
    status: str,
    error_message: str | None,
) -> None:
    # Prateek: DB write is isolated so a tracking failure never crashes the route.
    try:
        row = LLMUsage(
            user_id=user_id,
            username=username,
            endpoint=endpoint,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_text=response_text,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
        )
        db.add(row)
        db.commit()
        logger.info(
            "LLM usage recorded",
            endpoint=endpoint,
            username=username,
            model=model,
            total_tokens=usage.get("total_tokens"),
            duration_ms=duration_ms,
            status=status,
        )
    except Exception:
        logger.exception("Failed to persist LLM usage record — call succeeded, tracking skipped")
        db.rollback()
