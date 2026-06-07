"""Script QA routes (design §12.5, §16.4 QA panel, §11.7 repair)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user
from ..observability import emit
from ..repositories import audio as audio_repo
from ..repositories import episodes as ep_repo
from ..repositories import personas as persona_repo
from ..repositories import projects as projects_repo
from ..repositories import qa as qa_repo
from ..repositories import scripts as scripts_repo
from ..scripting.estimate import estimate_seconds
from ..scripting.generator import rewrite_segment
from ..services.queue import get_queue

router = APIRouter(tags=["qa"])


def _owned_version(version_id: str, user: dict) -> dict:
    v = scripts_repo.get_version_by_id(version_id)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Script version not found.")
    ep = ep_repo.get_episode(str(v["episode_id"]))
    project = projects_repo.get_project(str(ep["project_id"])) if ep else None
    if project is None or str(project["user_id"]) != str(user["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your script.")
    return v


@router.post("/api/scripts/{script_version_id}/qa", status_code=status.HTTP_202_ACCEPTED)
def run_qa(script_version_id: str, user: dict = Depends(get_current_user)):
    v = _owned_version(script_version_id, user)
    job = get_queue().enqueue("script_qa", {"script_version_id": script_version_id},
                              episode_id=str(v["episode_id"]))
    return {"job_id": str(job["id"]), "status": "queued"}


@router.get("/api/scripts/{script_version_id}/qa")
def get_qa(script_version_id: str, user: dict = Depends(get_current_user)):
    v = _owned_version(script_version_id, user)
    reports = [{"report_type": r["report_type"], "score": r["score_json"],
                "warnings": r["warnings"]} for r in qa_repo.list_reports(script_version_id)]
    if not reports:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No QA yet. Run QA first.")
    return {"script_version_id": script_version_id,
            "safety_status": v["safety_status"], "summary": v["qa_summary"],
            "reports": reports}


@router.post("/api/scripts/{script_version_id}/repair")
def repair(script_version_id: str, user: dict = Depends(get_current_user)):
    """One-click repair: LLM-rewrite every needs_review segment to address its
    QA warnings (design §11.7 high-severity path)."""
    from ..providers.llm import get_llm_provider

    v = _owned_version(script_version_id, user)
    episode_id = str(v["episode_id"])
    role_by_label = {p["speaker_label"]: p["role"] for p in ep_repo.list_personas(episode_id)}
    provider = get_llm_provider()

    repaired = []
    for seg in scripts_repo.list_needs_review(script_version_id):
        warnings = (seg["qa_json"] or {}).get("warnings", [])
        instruction = "Address these QA notes while staying in character: " + \
            "; ".join(w.get("suggested_action") or w["message"] for w in warnings) \
            or "Improve this line."
        brief = ""
        if seg["speaker_persona_version_id"]:
            pv = persona_repo.get_version_by_id(str(seg["speaker_persona_version_id"]))
            if pv:
                brief = "forbidden: " + "; ".join(pv["forbidden_moves"] or [])
        new_text = rewrite_segment(provider,
                                   {"speaker_label": seg["speaker_label"], "text": seg["text"]},
                                   instruction, brief)
        role = role_by_label.get(seg["speaker_label"], "guest")
        scripts_repo.update_segment_text(str(seg["id"]), new_text,
                                         estimate_seconds(new_text, role))
        audio_repo.mark_segment_audio_stale(str(seg["id"]))
        repaired.append(str(seg["id"]))

    if repaired:
        audio_repo.mark_episode_mixes_stale(episode_id)
    emit("segment_rerendered", episode_id=episode_id, count=len(repaired), mode="qa_repair")
    return {"repaired_segment_ids": repaired, "count": len(repaired),
            "note": "Re-run QA to refresh scores after repair."}
