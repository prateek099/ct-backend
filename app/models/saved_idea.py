"""SavedIdea ORM — user's personal idea bank."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SavedIdea(Base):
    __tablename__ = "saved_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    angle: Mapped[str | None] = mapped_column(String(100), nullable=True)
    format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "content_hash", name="uq_saved_ideas_user_hash"),
        Index("ix_saved_ideas_user_created", "user_id", "created_at"),
    )
