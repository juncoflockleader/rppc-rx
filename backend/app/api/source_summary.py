"""Top-level source endpoints (design §12.2): summary + evidence view.

GET /api/sources/{source_id}/summary -> summary, themes, claims.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user
from ..repositories import claims as claims_repo
from ..repositories import projects as projects_repo
from ..repositories import sources as sources_repo

router = APIRouter(prefix="/api/sources", tags=["sources"])


def _owned_source(source_id: str, user: dict) -> dict:
    src = sources_repo.get_source(source_id)
    if src is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")
    project = projects_repo.get_project(str(src["project_id"]))
    if project is None or str(project["user_id"]) != str(user["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your source.")
    return src


@router.get("/{source_id}/summary")
def get_summary(source_id: str, user: dict = Depends(get_current_user)):
    src = _owned_source(source_id, user)
    meta = src.get("metadata") or {}
    rows = claims_repo.list_claims(source_id)
    return {
        "source_id": source_id,
        "status": src["status"],
        "summary": meta.get("summary"),
        "themes": meta.get("themes", []),
        "claims": [
            {
                "claim_id": str(r["id"]),
                "claim_text": r["claim_text"],
                "claim_type": r["claim_type"],
                "page_number": r["page_number"],
                "confidence": float(r["confidence"]) if r["confidence"] is not None else None,
            }
            for r in rows
        ],
    }
