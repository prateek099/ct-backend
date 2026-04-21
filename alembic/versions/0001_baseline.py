"""baseline — users + llm_usage

Revision ID: 0001_baseline
Revises:
Create Date: 2026-04-21

Idempotent: if the tables already exist (e.g. they were created by the legacy
`Base.metadata.create_all()` call), this migration skips them rather than
failing. That lets existing environments upgrade cleanly without a manual
`alembic stamp`.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True, index=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    if "llm_usage" not in existing:
        op.create_table(
            "llm_usage",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("username", sa.String(length=100), nullable=False, index=True),
            sa.Column("endpoint", sa.String(length=100), nullable=False, index=True),
            sa.Column("model", sa.String(length=100), nullable=False),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column("user_prompt", sa.Text(), nullable=False),
            sa.Column("response_text", sa.Text(), nullable=True),
            sa.Column("prompt_tokens", sa.Integer(), nullable=True),
            sa.Column("completion_tokens", sa.Integer(), nullable=True),
            sa.Column("total_tokens", sa.Integer(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                index=True,
            ),
        )


def downgrade() -> None:
    op.drop_table("llm_usage")
    op.drop_table("users")
