"""Voice direction (design §11.8).

Rule-based: derive each segment's delivery metadata from its persona's
voice_profile (M3). Deterministic and free — no LLM call. The host is clear and
guiding; Laozi slow and spacious; Buddha calm and measured — straight from each
asset's voice_profile.
"""
from __future__ import annotations

from typing import Any, Dict

_DEFAULT_PAUSE_MS = 400


def voice_id_for(persona_id: str) -> str:
    return f"voice_{persona_id}_default"


def build_delivery(voice_profile: Dict[str, Any]) -> Dict[str, Any]:
    vp = voice_profile or {}
    hints = vp.get("tts_hints") or {}
    return {
        "tone": vp.get("tone", "neutral"),
        "pace": vp.get("pace", "medium"),
        "emotion": vp.get("emotional_range", "balanced"),
        "pause_before_ms": 0,
        "pause_after_ms": int(hints.get("default_pause_after_ms", _DEFAULT_PAUSE_MS)),
        "emphasis": [],
        "pronunciation_notes": [],
    }
