"""Persona library routes (design §12.3). M1: read-only from YAML seeds."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user
from ..services.persona_loader import get_persona, load_personas

router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("")
def list_personas(_user: dict = Depends(get_current_user)):
    # Card-level summary; full asset is fetched per version.
    out = []
    for p in load_personas():
        out.append({
            "persona_id": p.get("persona_id"),
            "version": p.get("version"),
            "display_name": p.get("display_name"),
            "type": p.get("type"),
            "status": p.get("status"),
            "summary": (p.get("identity_profile") or {}).get("summary"),
        })
    return out


@router.get("/{persona_id}/versions/{version}")
def get_persona_version(persona_id: str, version: str,
                        _user: dict = Depends(get_current_user)):
    p = get_persona(persona_id, version)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Persona version not found.")
    return p
