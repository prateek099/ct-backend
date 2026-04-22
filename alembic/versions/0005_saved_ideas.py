"""saved_ideas — user-saved video idea bank

Revision ID: 0005_saved_ideas
Revises: 0004_prompt_overrides
Create Date: 2026-04-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0005_saved_ideas"
down_revision: Union[str, None] = "0004_prompt_overrides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "saved_ideas" in _existing_tables():
        return

    op.create_table(
        "saved_ideas",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("hook", sa.Text(), nullable=True),
        sa.Column("angle", sa.String(length=100), nullable=True),
        sa.Column("format", sa.String(length=100), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("source_prompt", sa.Text(), nullable=True),
        sa.Column(
            "source_project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "content_hash", name="uq_saved_ideas_user_hash"
        ),
    )
    op.create_index(
        "ix_saved_ideas_user_created",
        "saved_ideas",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    if "saved_ideas" not in _existing_tables():
        return
    op.drop_index("ix_saved_ideas_user_created", table_name="saved_ideas")
    op.drop_table("saved_ideas")
