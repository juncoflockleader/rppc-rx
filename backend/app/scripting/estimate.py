"""Audio-duration estimation from text (design §27.1).

English words-per-second by role; corrected later by real TTS duration (M7).
"""
from __future__ import annotations

WPS_BY_ROLE = {"host": 2.5, "guest": 2.0, "student": 2.4, "critic": 2.1}
DEFAULT_WPS = 2.2


def estimate_seconds(text: str, role: str = "guest") -> int:
    words = len(text.split())
    wps = WPS_BY_ROLE.get(role, DEFAULT_WPS)
    return max(1, round(words / wps))
