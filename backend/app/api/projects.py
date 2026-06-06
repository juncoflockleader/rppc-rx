"""Project routes (design §12.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from ..auth import get_current_user, require_project_owner
from ..observability import emit
from ..repositories import projects as projects_repo
from ..services.storage import get_storage
from ..schemas import CreateProjectRequest, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(body: CreateProjectRequest, user: dict = Depends(get_current_user)):
    row = projects_repo.create_project(
        user_id=str(user["id"]),
        title=body.title,
        description=body.description,
        default_language=body.default_language,
    )
    emit("project_created", project_id=str(row["id"]), user_id=str(user["id"]))
    return ProjectOut.from_row(row)


@router.get("", response_model=list[ProjectOut])
def list_projects(user: dict = Depends(get_current_user)):
    return [ProjectOut.from_row(r) for r in projects_repo.list_projects(str(user["id"]))]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: dict = Depends(require_project_owner)):
    return ProjectOut.from_row(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project: dict = Depends(require_project_owner)):
    project_id = str(project["id"])
    # Remove blobs first (sources/audio/exports), then DB rows cascade (§19.4).
    prefix = f"users/{project['user_id']}/projects/{project_id}"
    try:
        get_storage().delete_prefix(prefix)
    except Exception:  # storage cleanup is best-effort; never block the delete
        pass
    projects_repo.delete_project(project_id)
    emit("project_deleted", project_id=project_id, user_id=str(project["user_id"]))
