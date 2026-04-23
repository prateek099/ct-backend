"""Project CRUD routes — list / create / get / patch / delete / publish. All owner-scoped."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new project owned by the caller."""
    return project_service.create_project(db, current_user, payload)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    # Prateek: Accepts a single status or comma-separated values (e.g. "draft,saved")
    # so Dashboard can fetch In-Flight projects in one request.
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the caller's projects, newest-updated first."""
    return project_service.list_projects(
        db, current_user, status=status_filter, limit=limit, offset=offset
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a single project by id. 404 if not owned by the caller."""
    return project_service.get_project(db, current_user, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Partial update. Only fields present in the body are written."""
    return project_service.update_project(db, current_user, project_id, payload)


@router.post("/{project_id}/publish", response_model=ProjectResponse)
async def publish_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a project as published. 409 if already published."""
    return project_service.publish_project(db, current_user, project_id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a project. 404 if not owned by the caller."""
    project_service.delete_project(db, current_user, project_id)
