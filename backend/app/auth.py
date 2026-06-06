"""Minimal auth (design §6.2). DEV STUB — replace before beta.

M1 accepts a single shared bearer token from the environment and maps every
request to a single dev user. The dependency signature is what real JWT auth
will use, so swapping the body later won't ripple through the routers.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from .config import get_settings
from .repositories import projects as projects_repo


def get_current_user(authorization: str = Header(default="")) -> dict:
    settings = get_settings()
    token = authorization.removeprefix("Bearer ").strip()
    if not token or token != settings.dev_bearer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return projects_repo.ensure_dev_user()


def require_project_owner(project_id: str, user: dict = Depends(get_current_user)) -> dict:
    project = projects_repo.get_project(project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found.")
    if str(project["user_id"]) != str(user["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your project.")
    return project
