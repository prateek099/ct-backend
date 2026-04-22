"""calendar_events — content calendar entries per user

Revision ID: 0007_calendar_events
Revises: 0006_channels
Create Date: 2026-04-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0007_calendar_events"
down_revision: Union[str, None] = "0006_channels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "calendar_events" in _existing_tables():
        return

    op.create_table(
        "calendar_events",
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
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recurrence_rule", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "event_type IN ('record','edit','publish','custom')",
            name="ck_calendar_events_type",
        ),
    )
    op.create_index(
        "ix_calendar_events_user_scheduled",
        "calendar_events",
        ["user_id", "scheduled_for"],
    )


def downgrade() -> None:
    if "calendar_events" not in _existing_tables():
        return
    op.drop_index("ix_calendar_events_user_scheduled", table_name="calendar_events")
    op.drop_table("calendar_events")
