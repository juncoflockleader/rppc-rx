"""Script + segment routes (design §12.5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..observability import emit
from ..repositories import audio as audio_repo
from ..repositories import episodes as ep_repo
from ..repositories import personas as persona_repo
from ..repositories import projects as projects_repo
from ..repositories import scripts as scripts_repo
from ..scripting.estimate import estimate_seconds
from ..scripting.generator import rewrite_segment
from ..services.queue import get_queue

router = APIRouter(tags=["scripts"])


class UpdateSegmentRequest(BaseModel):
    text: str = Field(min_length=1)


class RewriteSegmentRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=500)


def _owned_episode(episode_id: str, user: dict) -> dict:
    ep = ep_repo.get_episode(episode_id)
    if ep is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Episode not found.")
    project = projects_repo.get_project(str(ep["project_id"]))
    if project is None or str(project["user_id"]) != str(user["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your episode.")
    return ep


def _owned_segment(segment_id: str, user: dict) -> tuple:
    seg = scripts_repo.get_segment(segment_id)
    if seg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Segment not found.")
    ep = _owned_episode(str(seg["episode_id"]), user)
    return seg, ep


def _role_for_label(episode_id: str, label: str) -> str:
    for p in ep_repo.list_personas(episode_id):
        if p["speaker_label"] == label:
            return p["role"]
    return "guest"


def _invalidate_audio(segment_id: str, episode_id: str) -> None:
    """Editing a line makes its rendered audio and the final mix stale (§4.2)."""
    audio_repo.mark_segment_audio_stale(segment_id)
    audio_repo.mark_episode_mixes_stale(episode_id)


# --- script generation / read ----------------------------------------------

@router.post("/api/episodes/{episode_id}/scripts", status_code=status.HTTP_202_ACCEPTED)
def generate(episode_id: str, user: dict = Depends(get_current_user)):
    ep = _owned_episode(episode_id, user)
    if ep_repo.get_latest_plan(episode_id) is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "No discussion plan yet. Generate the plan first.")
    job = get_queue().enqueue("script_generation", {"episode_id": episode_id},
                              project_id=str(ep["project_id"]), episode_id=episode_id)
    return {"job_id": str(job["id"]), "status": "queued"}


@router.get("/api/episodes/{episode_id}/scripts/latest")
def latest(episode_id: str, user: dict = Depends(get_current_user)):
    _owned_episode(episode_id, user)
    version = scripts_repo.get_latest(episode_id)
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No script yet. Generate one first.")
    segments = []
    for s in scripts_repo.list_segments(str(version["id"])):
        ev = [{"type": e["evidence_type"], "claim_id": str(e["source_claim_id"])
               if e["source_claim_id"] else None, "concept": e["concept"],
               "notes": e["notes"]} for e in scripts_repo.list_evidence(str(s["id"]))]
        segments.append({
            "id": str(s["id"]), "segment_index": s["segment_index"],
            "beat_id": s["beat_id"], "speaker_label": s["speaker_label"],
            "text": s["text"], "estimated_seconds": s["estimated_seconds"],
            "status": s["status"], "evidence": ev,
        })
    return {"episode_id": episode_id, "script_version_id": str(version["id"]),
            "version": version["version"], "status": version["status"],
            "safety_status": version["safety_status"],
            "total_estimated_seconds": version["total_estimated_seconds"],
            "metadata": version["metadata"], "segments": segments}


# --- segment edit / rewrite -------------------------------------------------

@router.patch("/api/script-segments/{segment_id}")
def update_segment(segment_id: str, body: UpdateSegmentRequest,
                   user: dict = Depends(get_current_user)):
    seg, _ = _owned_segment(segment_id, user)
    role = _role_for_label(str(seg["episode_id"]), seg["speaker_label"])
    row = scripts_repo.update_segment_text(
        segment_id, body.text, estimate_seconds(body.text, role))
    _invalidate_audio(segment_id, str(seg["episode_id"]))
    emit("segment_rewritten", episode_id=str(seg["episode_id"]), segment_id=segment_id,
         mode="manual_edit")
    return {"id": str(row["id"]), "text": row["text"],
            "estimated_seconds": row["estimated_seconds"], "status": row["status"]}


@router.post("/api/script-segments/{segment_id}/rewrite")
def rewrite(segment_id: str, body: RewriteSegmentRequest,
            user: dict = Depends(get_current_user)):
    from ..providers.llm import get_llm_provider

    seg, _ = _owned_segment(segment_id, user)
    role = _role_for_label(str(seg["episode_id"]), seg["speaker_label"])

    # Persona constraints for the rewrite (stay in character).
    brief = ""
    if seg["speaker_persona_version_id"]:
        v = persona_repo.get_version_by_id(str(seg["speaker_persona_version_id"]))
        if v:
            forbidden = "; ".join(v["forbidden_moves"] or [])
            style = (v["style_profile"] or {}).get("tone", "")
            brief = f"tone: {style}; forbidden: {forbidden}"

    new_text = rewrite_segment(get_llm_provider(),
                               {"speaker_label": seg["speaker_label"], "text": seg["text"]},
                               body.instruction, brief)
    row = scripts_repo.update_segment_text(segment_id, new_text, estimate_seconds(new_text, role))
    _invalidate_audio(segment_id, str(seg["episode_id"]))
    emit("segment_rewritten", episode_id=str(seg["episode_id"]), segment_id=segment_id,
         mode="llm_rewrite")
    return {"id": str(row["id"]), "text": row["text"],
            "estimated_seconds": row["estimated_seconds"], "status": row["status"]}
