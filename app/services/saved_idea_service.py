"""Idea-bank service — persists a user's saved ideas with de-dup by content hash."""
import hashlib

from sqlalchemy.orm import Session

from app.api.deps import get_owned_or_404
from app.models.saved_idea import SavedIdea
from app.models.user import User
from app.schemas.saved_idea import SavedIdeaCreate


def _hash_idea(title: str, hook: str | None) -> str:
    # Prateek: title + hook is stable enough to dedupe repeat Save clicks without
    # blocking genuinely different ideas that happen to share a title.
    raw = f"{title.strip().lower()}::{(hook or '').strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_idea(db: Session, user: User, payload: SavedIdeaCreate) -> SavedIdea:
    content_hash = _hash_idea(payload.title, payload.hook)

    existing = (
        db.query(SavedIdea)
        .filter(SavedIdea.user_id == user.id, SavedIdea.content_hash == content_hash)
        .first()
    )
    if existing is not None:
        return existing

    idea = SavedIdea(
        user_id=user.id,
        title=payload.title,
        hook=payload.hook,
        angle=payload.angle,
        format=payload.format,
        reasoning=payload.reasoning,
        source_prompt=payload.source_prompt,
        source_project_id=payload.source_project_id,
        content_hash=content_hash,
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


def list_ideas(
    db: Session, user: User, limit: int = 50, offset: int = 0
) -> list[SavedIdea]:
    return (
        db.query(SavedIdea)
        .filter(SavedIdea.user_id == user.id)
        .order_by(SavedIdea.created_at.desc(), SavedIdea.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def delete_idea(db: Session, user: User, idea_id: int) -> None:
    idea = get_owned_or_404(db, SavedIdea, idea_id, user)
    db.delete(idea)
    db.commit()
