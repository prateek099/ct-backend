"""SQLAlchemy engine, Base, and get_db session dependency."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Prateek: Render issues postgres:// URLs (deprecated scheme); SQLAlchemy 2.0 also
# defaults postgresql:// to psycopg2. Normalise both to postgresql+psycopg:// so we
# always go through psycopg3.
_url = settings.database_url
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql+psycopg://", 1)
elif _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+psycopg://", 1)

# Prateek: Runtime is Postgres-only. Tests build their own engine in conftest.py,
# so this guard only fires when the app boots with a stale sqlite:// in .env.
if _url.startswith("sqlite"):
    raise RuntimeError(
        "DATABASE_URL points at SQLite, but the app is Postgres-only at runtime. "
        "Update your .env to a postgresql+psycopg:// URL (docker-compose default: "
        "postgresql+psycopg://ct_user:ct_pass@db:5432/creator_tools)."
    )

engine = create_engine(_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
