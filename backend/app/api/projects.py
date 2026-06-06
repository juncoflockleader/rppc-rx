"""Project routes (design §12.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from ..auth import get_current_user, require_project_owner
from ..repositories import projects as projects_repo
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
    return ProjectOut.from_row(row)


@router.get("", response_model=list[ProjectOut])
def list_projects(user: dict = Depends(get_current_user)):
    return [ProjectOut.from_row(r) for r in projects_repo.list_projects(str(user["id"]))]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: dict = Depends(require_project_owner)):
    return ProjectOut.from_row(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project: dict = Depends(require_project_owner)):
    projects_repo.delete_project(str(project["id"]))
