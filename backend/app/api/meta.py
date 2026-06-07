"""Notices, feedback, cost, and admin debug routes (design §19.2, §12 feedback,
§20.3-20.4)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..config import get_settings
from ..notices import notices
from ..observability import emit
from ..repositories import episodes as ep_repo
from ..repositories import exports as exports_repo
from ..repositories import projects as projects_repo

router = APIRouter(tags=["meta"])


# --- notices (public) -------------------------------------------------------

@router.get("/api/meta/notices")
def get_notices():
    return notices()


# --- feedback ---------------------------------------------------------------

class FeedbackRequest(BaseModel):
    target_type: str                     # episode | script_segment | audio | persona
    target_id: Optional[str] = None
    feedback_type: str = "thumbs"        # thumbs | tag | comment
    rating: Optional[int] = None         # -1 / +1 or 1..5
    tags: Optional[list] = None
    comment: Optional[str] = Field(default=None, max_length=2000)
    project_id: Optional[str] = None
    episode_id: Optional[str] = None


@router.post("/api/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(body: FeedbackRequest, user: dict = Depends(get_current_user)):
    row = exports_repo.insert_feedback(
        user_id=str(user["id"]), project_id=body.project_id, episode_id=body.episode_id,
        target_type=body.target_type, target_id=body.target_id,
        feedback_type=body.feedback_type, rating=body.rating, tags=body.tags,
        comment=body.comment)
    emit("feedback_submitted", target_type=body.target_type, feedback_type=body.feedback_type)
    return {"id": str(row["id"]), "status": "recorded"}


# --- cost (per episode) -----------------------------------------------------

@router.get("/api/episodes/{episode_id}/cost")
def episode_cost(episode_id: str, user: dict = Depends(get_current_user)):
    ep = ep_repo.get_episode(episode_id)
    if ep is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Episode not found.")
    project = projects_repo.get_project(str(ep["project_id"]))
    if project is None or str(project["user_id"]) != str(user["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your episode.")

    s = get_settings()
    u = exports_repo.usage_summary_for_episode(episode_id)
    in_tok = int(u["llm_input_tokens"]); out_tok = int(u["llm_output_tokens"])
    est = round(in_tok / 1e6 * s.llm_input_price_per_m
                + out_tok / 1e6 * s.llm_output_price_per_m, 4)
    return {"episode_id": episode_id,
            "llm_input_tokens": in_tok, "llm_output_tokens": out_tok,
            "llm_calls": int(u["llm_calls"]),
            "tts_chars": int(u["tts_chars"]), "tts_duration_ms": int(u["tts_duration_ms"]),
            "tts_calls": int(u["tts_calls"]),
            "estimated_llm_cost_usd": est}


# --- admin debug trace ------------------------------------------------------

@router.get("/api/admin/usage")
def admin_usage(episode_id: Optional[str] = None,
                x_admin_token: str = Header(default="")):
    s = get_settings()
    if not s.admin_token or x_admin_token != s.admin_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required.")
    rows = exports_repo.recent_usage(episode_id, limit=200)
    return {"events": [
        {"kind": r["kind"], "task_name": r["task_name"], "model": r["model"],
         "input_tokens": r["input_tokens"], "output_tokens": r["output_tokens"],
         "char_count": r["char_count"], "latency_ms": r["latency_ms"],
         "episode_id": str(r["episode_id"]) if r["episode_id"] else None,
         "created_at": r["created_at"].isoformat()} for r in rows]}
