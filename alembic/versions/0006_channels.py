"""channels — per-user saved YouTube channel snapshots

Revision ID: 0006_channels
Revises: 0005_saved_ideas
Create Date: 2026-04-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0006_channels"
down_revision: Union[str, None] = "0005_saved_ideas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "channels" in _existing_tables():
        return

    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("youtube_channel_id", sa.String(length=50), nullable=False),
        sa.Column("channel_name", sa.String(length=255), nullable=False),
        sa.Column("handle", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subscriber_count", sa.Integer(), nullable=True),
        sa.Column("total_views", sa.BigInteger(), nullable=True),
        sa.Column("video_count", sa.Integer(), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("recent_videos_json", sa.JSON(), nullable=True),
        sa.Column("average_duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "last_refreshed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "youtube_channel_id", name="uq_channels_user_yt"
        ),
    )


def downgrade() -> None:
    if "channels" in _existing_tables():
        op.drop_table("channels")
