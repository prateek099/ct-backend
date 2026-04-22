"""TrendingCache ORM — cached YouTube most-popular results per region/category."""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrendingCache(Base):
    __tablename__ = "trending_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    region: Mapped[str] = mapped_column(String(10), nullable=False)
    category_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    data: Mapped[Any] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "region", "category_id", name="ux_trending_cache_region_category"
        ),
    )
