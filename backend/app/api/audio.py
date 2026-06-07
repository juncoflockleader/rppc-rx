"""Audio routes (design §12.6, §11.9, §19.5 gate)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from ..auth import get_current_user
from ..repositories import audio as audio_repo
from ..repositories import episodes as ep_repo
from ..repositories import projects as projects_repo
from ..repositories import scripts as scripts_repo
from ..services.queue import get_queue
from ..services.storage import get_storage

router = APIRouter(tags=["audio"])


def _owned_episode(episode_id: str, user: dict) -> dict:
    ep = ep_repo.get_episode(episode_id)
    if ep is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Episode not found.")
    project = projects_repo.get_project(str(ep["project_id"]))
    if project is None or str(project["user_id"]) != str(user["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your episode.")
    return ep


def _require_renderable(episode_id: str) -> dict:
    version = scripts_repo.get_latest(episode_id)
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No script yet. Generate a script first.")
    if version["safety_status"] == "high_risk":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This script is flagged high_risk by QA and cannot be rendered. "
            "Resolve the safety warnings and re-run QA first.")
    return version


@router.post("/api/episodes/{episode_id}/audio", status_code=status.HTTP_202_ACCEPTED)
def render_audio(episode_id: str, user: dict = Depends(get_current_user)):
    ep = _owned_episode(episode_id, user)
    version = _require_renderable(episode_id)
    job = get_queue().enqueue(
        "audio_render",
        {"episode_id": episode_id, "script_version_id": str(version["id"])},
        project_id=str(ep["project_id"]), episode_id=episode_id)
    return {"job_id": str(job["id"]), "status": "queued"}


@router.post("/api/script-segments/{segment_id}/audio", status_code=status.HTTP_202_ACCEPTED)
def rerender_segment(segment_id: str, user: dict = Depends(get_current_user)):
    seg = scripts_repo.get_segment(segment_id)
    if seg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Segment not found.")
    ep = _owned_episode(str(seg["episode_id"]), user)
    _require_renderable(str(seg["episode_id"]))
    job = get_queue().enqueue(
        "audio_render",
        {"episode_id": str(seg["episode_id"]),
         "script_version_id": str(seg["script_version_id"]), "segment_id": segment_id},
        project_id=str(ep["project_id"]), episode_id=str(seg["episode_id"]))
    return {"job_id": str(job["id"]), "status": "queued"}


@router.get("/api/episodes/{episode_id}/audio/latest")
def latest_audio(episode_id: str, user: dict = Depends(get_current_user)):
    _owned_episode(episode_id, user)
    mix = audio_repo.get_latest_mix(episode_id)
    if mix is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No audio yet. Render first.")
    return {
        "episode_id": episode_id,
        "mix_id": str(mix["id"]),
        "status": mix["status"],          # completed | stale
        "format": mix["format"],
        "duration_ms": mix["duration_ms"],
        "download_url": f"/api/audio-mixes/{mix['id']}/download",
    }


@router.get("/api/audio-mixes/{mix_id}/download")
def download_mix(mix_id: str, user: dict = Depends(get_current_user)):
    mix = audio_repo.get_mix(mix_id)
    if mix is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mix not found.")
    _owned_episode(str(mix["episode_id"]), user)
    data = get_storage().get(mix["audio_uri"])
    media = "audio/wav" if mix["format"] == "wav" else "audio/mpeg"
    return Response(content=data, media_type=media,
                    headers={"Content-Disposition":
                             f'attachment; filename="episode_{mix["episode_id"]}.{mix["format"]}"'})
