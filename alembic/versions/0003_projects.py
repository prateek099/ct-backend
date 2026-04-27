"""projects — add projects table + llm_usage.project_id

Revision ID: 0003_projects
Revises: 0002_foundation
Create Date: 2026-04-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0003_projects"
down_revision: Union[str, None] = "0002_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _column_exists(table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    # Prateek: Create projects table — resumable container for idea→script→title→seo.
    if "projects" not in _existing_tables():
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="draft",
            ),
            sa.Column("channel_id", sa.Integer(), nullable=True),
            sa.Column("idea_json", sa.JSON(), nullable=True),
            sa.Column("script_json", sa.JSON(), nullable=True),
            sa.Column("title_json", sa.JSON(), nullable=True),
            sa.Column("seo_json", sa.JSON(), nullable=True),
            sa.Column("slug", sa.String(length=80), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.CheckConstraint(
                "status IN ('draft','published','archived')",
                name="ck_projects_status",
            ),
        )
        op.create_index(
            "ix_projects_user_status_updated",
            "projects",
            ["user_id", "status", sa.text("updated_at DESC")],
        )

    # Prateek: Add llm_usage.project_id so we can attribute cost to a project.
    if not _column_exists("llm_usage", "project_id"):
        op.add_column(
            "llm_usage",
            sa.Column("project_id", sa.Integer(), nullable=True, index=True),
        )
        op.create_foreign_key(
            "fk_llm_usage_project_id",
            "llm_usage",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if _column_exists("llm_usage", "project_id"):
        op.drop_constraint("fk_llm_usage_project_id", "llm_usage", type_="foreignkey")
        op.drop_column("llm_usage", "project_id")

    if "projects" in _existing_tables():
        op.drop_index("ix_projects_user_status_updated", table_name="projects")
        op.drop_table("projects")
