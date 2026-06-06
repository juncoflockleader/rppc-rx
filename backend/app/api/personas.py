"""Persona library routes (design §12.3). M3: DB-backed (populated by import).

Run `python -m app.personas_import` (or `make seed-personas`) after migrations
to populate persona_assets / persona_versions / persona_canon.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user
from ..repositories import personas as repo

router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("")
def list_personas(_user: dict = Depends(get_current_user)):
    out = []
    for r in repo.list_assets_with_latest():
        identity = r.get("identity_profile") or {}
        out.append({
            "persona_id": r["id"],
            "version": r["version"],
            "display_name": r["display_name"],
            "type": r["type"],
            "status": r["version_status"],
            "summary": identity.get("summary"),
        })
    return out


@router.get("/{persona_id}/versions/{version}")
def get_persona_version(persona_id: str, version: str,
                        _user: dict = Depends(get_current_user)):
    v = repo.get_version(persona_id, version)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Persona version not found.")
    asset = repo.get_asset(persona_id) or {}
    return {
        "persona_id": persona_id,
        "version": v["version"],
        "display_name": asset.get("display_name"),
        "type": asset.get("type"),
        "status": v["status"],
        "identity_profile": v["identity_profile"],
        "knowledge_boundary": v["knowledge_boundary"],
        "stance_matrix": v["stance_matrix"],
        "style_profile": v["style_profile"],
        "forbidden_moves": v["forbidden_moves"],
        "voice_profile": v["voice_profile"],
        "prompt_pack": v["prompt_pack"],
        "eval_summary": v["eval_summary"],
        "release_notes": v["release_notes"],
    }
