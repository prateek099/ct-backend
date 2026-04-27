"""ABTest ORM — title A/B experiments tied to a project."""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ABTest(Base):
    __tablename__ = "ab_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    title_a: Mapped[str] = mapped_column(String(500), nullable=False)
    title_b: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running", server_default="running"
    )
    winner: Mapped[str | None] = mapped_column(String(1), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('running','completed','cancelled')",
            name="ck_ab_tests_status",
        ),
        CheckConstraint(
            "winner IN ('a','b') OR winner IS NULL",
            name="ck_ab_tests_winner",
        ),
        Index("ix_ab_tests_project", "project_id"),
        Index(
            "ux_ab_tests_one_running_per_project",
            "project_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
            # Prateek: kept so the SQLite-backed test suite gets the same partial-
            # uniqueness semantics as the Postgres runtime. Runtime never reaches this.
            sqlite_where=text("status = 'running'"),
        ),
    )
