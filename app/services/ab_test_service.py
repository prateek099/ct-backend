"""A/B test service — per-user CRUD with project ownership + live-test uniqueness."""
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_owned_or_404
from app.core.exceptions import ConflictError, NotFoundError
from app.models.ab_test import ABTest
from app.models.project import Project
from app.models.user import User
from app.schemas.ab_test import ABTestCreate, ABTestUpdate


def _ensure_project_owned(db: Session, user: User, project_id: int) -> None:
    # Prateek: Ownership gate for the referenced project — reuse get_owned_or_404.
    get_owned_or_404(db, Project, project_id, user)


def create_ab_test(db: Session, user: User, payload: ABTestCreate) -> ABTest:
    _ensure_project_owned(db, user, payload.project_id)

    test = ABTest(user_id=user.id, **payload.model_dump())
    db.add(test)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "A running A/B test already exists for this project."
        )
    db.refresh(test)
    return test


def list_ab_tests(
    db: Session,
    user: User,
    project_id: Optional[int] = None,
    status: Optional[str] = None,
) -> list[ABTest]:
    q = db.query(ABTest).filter(ABTest.user_id == user.id)
    if project_id is not None:
        q = q.filter(ABTest.project_id == project_id)
    if status is not None:
        q = q.filter(ABTest.status == status)
    return q.order_by(ABTest.created_at.desc()).all()


def get_ab_test(db: Session, user: User, test_id: int) -> ABTest:
    return get_owned_or_404(db, ABTest, test_id, user)


def update_ab_test(
    db: Session, user: User, test_id: int, payload: ABTestUpdate
) -> ABTest:
    test = get_owned_or_404(db, ABTest, test_id, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(test, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "A running A/B test already exists for this project."
        )
    db.refresh(test)
    return test


def delete_ab_test(db: Session, user: User, test_id: int) -> None:
    test = get_owned_or_404(db, ABTest, test_id, user)
    db.delete(test)
    db.commit()
