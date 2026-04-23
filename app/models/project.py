"""Project ORM model — resumable container for idea → script → title → seo."""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )

    # Prateek: channel_id is a plain int until Feature 4 lands with the channels table.
    channel_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    idea_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    script_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    title_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    seo_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    thumbnail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    slug: Mapped[str | None] = mapped_column(String(80), nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','saved','published','archived')",
            name="ck_projects_status",
        ),
        Index("ix_projects_user_status_updated", "user_id", "status", "updated_at"),
    )
