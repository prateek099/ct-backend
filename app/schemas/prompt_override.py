"""Pydantic schemas for /admin/prompts."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

ToolName = Literal["ideas", "script", "title", "seo"]


class PromptOverrideUpdate(BaseModel):
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None


class PromptOverrideResponse(BaseModel):
    id: int
    tool: ToolName
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    updated_by_user_id: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptOverrideHistoryEntry(BaseModel):
    id: int
    tool: ToolName
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    updated_by_user_id: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}
