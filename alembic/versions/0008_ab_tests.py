"""ab_tests — title A/B experiments tied to a project

Revision ID: 0008_ab_tests
Revises: 0007_calendar_events
Create Date: 2026-04-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0008_ab_tests"
down_revision: Union[str, None] = "0007_calendar_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "ab_tests" in _existing_tables():
        return

    op.create_table(
        "ab_tests",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title_a", sa.String(length=500), nullable=False),
        sa.Column("title_b", sa.String(length=500), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="running"
        ),
        sa.Column("winner", sa.String(length=1), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('running','completed','cancelled')",
            name="ck_ab_tests_status",
        ),
        sa.CheckConstraint(
            "winner IN ('a','b') OR winner IS NULL",
            name="ck_ab_tests_winner",
        ),
    )
    op.create_index("ix_ab_tests_project", "ab_tests", ["project_id"])

    # Prateek: Partial unique index — at most one live test per project.
    op.create_index(
        "ux_ab_tests_one_running_per_project",
        "ab_tests",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
        sqlite_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    if "ab_tests" not in _existing_tables():
        return
    op.drop_index("ux_ab_tests_one_running_per_project", table_name="ab_tests")
    op.drop_index("ix_ab_tests_project", table_name="ab_tests")
    op.drop_table("ab_tests")
