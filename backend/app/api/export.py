"""Export routes (design §12.6, §6.8)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from ..auth import get_current_user
from ..repositories import episodes as ep_repo
from ..repositories import exports as exports_repo
from ..repositories import projects as projects_repo
from ..repositories import scripts as scripts_repo
from ..services.queue import get_queue
from ..services.storage import get_storage

router = APIRouter(tags=["export"])


def _owned_episode(episode_id: str, user: dict) -> dict:
    ep = ep_repo.get_episode(episode_id)
    if ep is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Episode not found.")
    project = projects_repo.get_project(str(ep["project_id"]))
    if project is None or str(project["user_id"]) != str(user["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your episode.")
    return ep


@router.post("/api/episodes/{episode_id}/export", status_code=status.HTTP_202_ACCEPTED)
def export_episode(episode_id: str, user: dict = Depends(get_current_user)):
    ep = _owned_episode(episode_id, user)
    if scripts_repo.get_latest(episode_id) is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No script to export yet.")
    job = get_queue().enqueue("export_package", {"episode_id": episode_id},
                              project_id=str(ep["project_id"]), episode_id=episode_id)
    return {"job_id": str(job["id"]), "status": "queued"}


@router.get("/api/episodes/{episode_id}/export/latest")
def latest_export(episode_id: str, user: dict = Depends(get_current_user)):
    _owned_episode(episode_id, user)
    exp = exports_repo.get_latest_export(episode_id)
    if exp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No export yet. Export first.")
    return {"episode_id": episode_id, "export_id": str(exp["id"]),
            "format": exp["format"], "manifest": exp["manifest"],
            "download_url": f"/api/exports/{exp['id']}/download"}


@router.get("/api/exports/{export_id}/download")
def download_export(export_id: str, user: dict = Depends(get_current_user)):
    exp = exports_repo.get_export(export_id)
    if exp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Export not found.")
    _owned_episode(str(exp["episode_id"]), user)
    data = get_storage().get(exp["package_uri"])
    return Response(content=data, media_type="application/zip",
                    headers={"Content-Disposition":
                             f'attachment; filename="episode_{exp["episode_id"]}.zip"'})
