"""trending_cache — cached YouTube trending results per region/category

Revision ID: 0009_trending_cache
Revises: 0008_ab_tests
Create Date: 2026-04-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0009_trending_cache"
down_revision: Union[str, None] = "0008_ab_tests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "trending_cache" in _existing_tables():
        return

    op.create_table(
        "trending_cache",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("region", sa.String(length=10), nullable=False),
        sa.Column("category_id", sa.String(length=10), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "region", "category_id", name="ux_trending_cache_region_category"
        ),
    )


def downgrade() -> None:
    if "trending_cache" not in _existing_tables():
        return
    op.drop_table("trending_cache")
