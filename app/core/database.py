"""SQLAlchemy engine, Base, and get_db session dependency."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Render injects postgresql:// or postgres:// — both default to psycopg2 in SQLAlchemy.
# Normalise to postgresql+psycopg:// so psycopg3 is always used.
_url = settings.database_url
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql+psycopg://", 1)
elif _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+psycopg://", 1)

# connect_args={"check_same_thread": False} is a SQLite-only parameter.
# Passing it to psycopg3 (or any other driver) raises a TypeError,
# so we inject it only when the URL targets SQLite.
_is_sqlite = _url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    _url,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
