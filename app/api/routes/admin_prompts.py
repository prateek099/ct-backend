"""Admin-only routes for managing AI prompt overrides."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.schemas.prompt_override import (
    PromptOverrideHistoryEntry,
    PromptOverrideResponse,
    PromptOverrideUpdate,
    ToolName,
)
from app.services import prompt_override_service

router = APIRouter(prefix="/admin/prompts", tags=["admin"])


@router.get("/", response_model=list[PromptOverrideResponse])
async def list_prompt_overrides(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Return every persisted override row, ordered by tool."""
    return prompt_override_service.list_overrides(db)


@router.get("/{tool}", response_model=PromptOverrideResponse)
async def get_prompt_override(
    tool: ToolName,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    override = prompt_override_service.get_override(db, tool)
    if override is None:
        raise NotFoundError(f"No override set for '{tool}'.")
    return override


@router.put("/{tool}", response_model=PromptOverrideResponse)
async def put_prompt_override(
    tool: ToolName,
    payload: PromptOverrideUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return prompt_override_service.upsert_override(db, tool, payload, admin)


@router.get("/{tool}/history", response_model=list[PromptOverrideHistoryEntry])
async def get_prompt_override_history(
    tool: ToolName,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return prompt_override_service.get_history(db, tool, limit=limit)
