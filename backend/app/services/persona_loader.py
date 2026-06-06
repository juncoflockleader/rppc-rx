"""Persona seed loader (design §15).

Reads versioned persona YAML from backend/personas/. In M1 this powers a
read-only persona library endpoint and the persona card UI. M3 adds the DB
import (persona_assets / persona_versions) and the canon vector index; the
YAML stays the authoring source of truth.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import yaml

PERSONAS_DIR = Path(__file__).resolve().parent.parent.parent / "personas"


@lru_cache
def load_personas() -> List[Dict[str, Any]]:
    personas: List[Dict[str, Any]] = []
    if not PERSONAS_DIR.is_dir():
        return personas
    for persona_dir in sorted(PERSONAS_DIR.iterdir()):
        if not persona_dir.is_dir():
            continue
        for yml in sorted(persona_dir.glob("v*.yaml")):
            with open(yml, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if data:
                personas.append(data)
    return personas


def get_persona(persona_id: str, version: str | None = None) -> Dict[str, Any] | None:
    for p in load_personas():
        if p.get("persona_id") == persona_id and (version is None or p.get("version") == version):
            return p
    return None
