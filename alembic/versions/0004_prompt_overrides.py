"""prompt_overrides — admin-editable system/user prompts per AI tool

Revision ID: 0004_prompt_overrides
Revises: 0003_projects
Create Date: 2026-04-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0004_prompt_overrides"
down_revision: Union[str, None] = "0003_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "prompt_overrides" not in existing:
        op.create_table(
            "prompt_overrides",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "tool",
                sa.String(length=50),
                nullable=False,
                unique=True,
                index=True,
            ),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column("user_prompt_template", sa.Text(), nullable=True),
            sa.Column(
                "updated_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
            sa.CheckConstraint(
                "tool IN ('ideas','script','title','seo')",
                name="ck_prompt_overrides_tool",
            ),
        )

    if "prompt_override_history" not in existing:
        op.create_table(
            "prompt_override_history",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("tool", sa.String(length=50), nullable=False, index=True),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column("user_prompt_template", sa.Text(), nullable=True),
            sa.Column(
                "updated_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )


def downgrade() -> None:
    if "prompt_override_history" in _existing_tables():
        op.drop_table("prompt_override_history")
    if "prompt_overrides" in _existing_tables():
        op.drop_table("prompt_overrides")
