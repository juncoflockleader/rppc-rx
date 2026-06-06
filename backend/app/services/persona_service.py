"""Persona usability + safety checks (design §19.1).

Before a persona can be attached to an episode it must be releasable and not a
prohibited persona type (no living/modern public figures, no voice clones).
"""
from __future__ import annotations

from fastapi import HTTPException, status

USABLE_STATUSES = {"active", "beta"}
PROHIBITED_TYPES = {
    "prohibited_modern_public_figure",
    "living_person",
    "voice_clone",
}


class PersonaNotUsable(Exception):
    pass


def validate_persona_usable(asset: dict, version: dict) -> None:
    """Raise PersonaNotUsable if this persona/version may not be used."""
    if asset.get("type") in PROHIBITED_TYPES:
        raise PersonaNotUsable(
            f"Persona '{asset.get('id')}' is a prohibited type "
            f"({asset.get('type')}) and cannot be used."
        )
    if version.get("status") not in USABLE_STATUSES:
        raise PersonaNotUsable(
            f"Persona '{asset.get('id')}' version '{version.get('version')}' is "
            f"'{version.get('status')}', not active or beta."
        )


def require_persona_usable(asset: dict, version: dict) -> None:
    """HTTP wrapper — 422 when a persona may not be used."""
    try:
        validate_persona_usable(asset, version)
    except PersonaNotUsable as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
