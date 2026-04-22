"""PromptOverride + history ORM models — admin-editable AI prompts."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PromptOverride(Base):
    __tablename__ = "prompt_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tool: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "tool IN ('ideas','script','title','seo')",
            name="ck_prompt_overrides_tool",
        ),
    )


class PromptOverrideHistory(Base):
    __tablename__ = "prompt_override_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tool: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
