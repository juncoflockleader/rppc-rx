"""Build export artifacts (design §2.4, §19.2): transcript, SRT, show notes,
evidence report. The interpretive-persona disclaimer is embedded in each."""
from __future__ import annotations

from typing import Any, Dict, List

from ..notices import DISCLAIMER_EN, SOURCE_COPYRIGHT


def _ts(ms: int) -> str:
    s, ms = divmod(int(ms), 1000)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def transcript_md(episode: Dict[str, Any], segments: List[Dict[str, Any]]) -> str:
    lines = [f"# {episode.get('title') or 'Episode'}", "", f"> {DISCLAIMER_EN}", ""]
    for s in segments:
        lines.append(f"**{s['speaker_label']}:** {s['text']}")
        lines.append("")
    return "\n".join(lines)


def transcript_srt(segments: List[Dict[str, Any]]) -> str:
    """segments carry duration_ms (from audio if rendered, else estimate)."""
    out = []
    cursor = 0
    for i, s in enumerate(segments, start=1):
        dur = int(s.get("duration_ms") or 1000)
        start, end = cursor, cursor + dur
        out += [str(i), f"{_ts(start)} --> {_ts(end)}",
                f"{s['speaker_label']}: {s['text']}", ""]
        cursor = end
    return "\n".join(out)


def show_notes_md(episode: Dict[str, Any], themes: List[str], takeaway: str,
                  participants: List[Dict[str, Any]]) -> str:
    goal = (episode.get("settings") or {}).get("goal") or ""
    cast = ", ".join(f"{p['speaker_label']} ({p.get('persona_id')})" for p in participants)
    lines = [
        f"# {episode.get('title') or 'Episode'} — Show Notes", "",
        f"**About:** {goal}", "",
        f"**Cast:** {cast}", "",
        f"**Themes:** {', '.join(themes) or '—'}", "",
        f"**Takeaway:** {takeaway or '—'}", "",
        "---", "", DISCLAIMER_EN, "", SOURCE_COPYRIGHT, "",
    ]
    return "\n".join(lines)


def evidence_report(episode: Dict[str, Any], segments: List[Dict[str, Any]],
                    claims_by_id: Dict[str, str]) -> Dict[str, Any]:
    seg_out = []
    for s in segments:
        ev = []
        for e in s.get("evidence", []):
            ev.append({"type": e["type"],
                       "claim_id": e.get("claim_id"),
                       "claim_text": claims_by_id.get(e.get("claim_id")) if e.get("claim_id") else None,
                       "concept": e.get("concept")})
        seg_out.append({"segment_index": s["segment_index"],
                        "speaker_label": s["speaker_label"], "text": s["text"],
                        "evidence": ev})
    return {"episode_id": str(episode["id"]), "title": episode.get("title"),
            "disclaimer": DISCLAIMER_EN, "segments": seg_out}
