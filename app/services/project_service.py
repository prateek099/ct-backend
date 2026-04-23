"""Project CRUD service — ownership-enforced.

Every read/write narrows by user_id via `get_owned_or_404` or direct filter,
so one user can never see or touch another user's projects.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.api.deps import get_owned_or_404
from app.core.exceptions import ConflictError
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate


def create_project(db: Session, user: User, payload: ProjectCreate) -> Project:
    project = Project(
        user_id=user.id,
        title=payload.title,
        status=payload.status,
        channel_id=payload.channel_id,
        idea_json=payload.idea_json,
        script_json=payload.script_json,
        title_json=payload.title_json,
        seo_json=payload.seo_json,
        thumbnail_json=payload.thumbnail_json,
        slug=payload.slug,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(
    db: Session,
    user: User,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Project]:
    query = db.query(Project).filter(Project.user_id == user.id)
    if status is not None:
        # Prateek: Support comma-separated values (e.g. "draft,saved") for
        # Dashboard In-Flight queries that need multiple statuses in one call.
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            query = query.filter(Project.status == statuses[0])
        else:
            query = query.filter(Project.status.in_(statuses))
    return (
        query.order_by(Project.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_project(db: Session, user: User, project_id: int) -> Project:
    return get_owned_or_404(db, Project, project_id, user)


def update_project(
    db: Session, user: User, project_id: int, payload: ProjectUpdate
) -> Project:
    project = get_owned_or_404(db, Project, project_id, user)
    # Prateek: only overwrite fields the caller explicitly sent (exclude_unset),
    # so partial PATCH doesn't stomp untouched JSON blobs with null.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def publish_project(db: Session, user: User, project_id: int) -> Project:
    project = get_owned_or_404(db, Project, project_id, user)
    if project.status == "published":
        raise ConflictError("Project is already published.")
    project.status = "published"
    project.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, user: User, project_id: int) -> None:
    project = get_owned_or_404(db, Project, project_id, user)
    db.delete(project)
    db.commit()
