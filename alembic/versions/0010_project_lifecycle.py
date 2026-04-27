"""project_lifecycle — add saved status, thumbnail_json, published_at

Revision ID: 0010_project_lifecycle
Revises: 0009_trending_cache
Create Date: 2026-04-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0010_project_lifecycle"
down_revision: Union[str, None] = "0009_trending_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names() -> set[str]:
    return {c["name"] for c in inspect(op.get_bind()).get_columns("projects")}


def upgrade() -> None:
    cols = _column_names()

    if "thumbnail_json" not in cols:
        op.add_column("projects", sa.Column("thumbnail_json", sa.JSON(), nullable=True))

    if "published_at" not in cols:
        op.add_column(
            "projects",
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        )

    # Prateek: Recreate the status constraint to include 'saved'.
    op.drop_constraint("ck_projects_status", "projects", type_="check")
    op.create_check_constraint(
        "ck_projects_status",
        "projects",
        "status IN ('draft','saved','published','archived')",
    )


def downgrade() -> None:
    cols = _column_names()

    op.drop_constraint("ck_projects_status", "projects", type_="check")
    op.create_check_constraint(
        "ck_projects_status",
        "projects",
        "status IN ('draft','published','archived')",
    )

    if "published_at" in cols:
        op.drop_column("projects", "published_at")

    if "thumbnail_json" in cols:
        op.drop_column("projects", "thumbnail_json")
