"""Prompt override service — admin can swap AI tool prompts without a redeploy.

Fallback lives in app/prompts/{tool}.py. This layer only returns an override
row if one exists and has at least one non-null field. Writes append to
prompt_override_history for audit.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.prompt_override import PromptOverride, PromptOverrideHistory
from app.models.user import User
from app.schemas.prompt_override import PromptOverrideUpdate


def get_override(db: Session, tool: str) -> Optional[PromptOverride]:
    return db.query(PromptOverride).filter(PromptOverride.tool == tool).first()


def resolve_prompts(
    db: Session,
    tool: str,
    default_system: str,
    default_template: str,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt_template) for `tool`, applying override if present."""
    # Prateek: read-only resolve — used by the AI routes' build() functions.
    override = get_override(db, tool)
    if override is None:
        return default_system, default_template
    system = override.system_prompt or default_system
    template = override.user_prompt_template or default_template
    return system, template


def list_overrides(db: Session) -> list[PromptOverride]:
    return db.query(PromptOverride).order_by(PromptOverride.tool).all()


def upsert_override(
    db: Session,
    tool: str,
    payload: PromptOverrideUpdate,
    user: User,
) -> PromptOverride:
    override = get_override(db, tool)
    if override is None:
        override = PromptOverride(
            tool=tool,
            system_prompt=payload.system_prompt,
            user_prompt_template=payload.user_prompt_template,
            updated_by_user_id=user.id,
        )
        db.add(override)
    else:
        if payload.system_prompt is not None:
            override.system_prompt = payload.system_prompt
        if payload.user_prompt_template is not None:
            override.user_prompt_template = payload.user_prompt_template
        override.updated_by_user_id = user.id

    db.flush()

    # Prateek: append-only audit entry so we can see who changed what, when.
    db.add(
        PromptOverrideHistory(
            tool=tool,
            system_prompt=override.system_prompt,
            user_prompt_template=override.user_prompt_template,
            updated_by_user_id=user.id,
        )
    )
    db.commit()
    db.refresh(override)
    return override


def get_history(db: Session, tool: str, limit: int = 50) -> list[PromptOverrideHistory]:
    return (
        db.query(PromptOverrideHistory)
        .filter(PromptOverrideHistory.tool == tool)
        .order_by(PromptOverrideHistory.id.desc())
        .limit(limit)
        .all()
    )
