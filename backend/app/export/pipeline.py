"""Export packaging pipeline (design §6.8, §2.4, §9).

Assembles transcript.md / transcript.srt / show_notes.md / evidence_report.json
(+ the audio mix if rendered) into a single zip in object storage.
"""
from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Callable, List, Optional

from ..repositories import audio as audio_repo
from ..repositories import claims as claims_repo
from ..repositories import episodes as ep_repo
from ..repositories import exports as exports_repo
from ..repositories import projects as projects_repo
from ..repositories import scripts as scripts_repo
from ..repositories import sources as sources_repo
from ..services.storage import get_storage
from . import builder

log = logging.getLogger("export")

ProgressFn = Optional[Callable[[float], None]]


def _tick(progress: ProgressFn, v: float) -> None:
    if progress:
        progress(v)


def build_export(episode_id: str, progress: ProgressFn = None) -> dict:
    episode = ep_repo.get_episode(episode_id)
    if episode is None:
        raise ValueError("episode not found")
    version = scripts_repo.get_latest(episode_id)
    if version is None:
        raise ValueError("no script to export; generate a script first")
    version_id = str(version["id"])

    project = projects_repo.get_project(str(episode["project_id"]))
    user_id = str(project["user_id"]) if project else "unknown"
    prefix = f"users/{user_id}/projects/{episode['project_id']}/episodes/{episode_id}"

    participants = ep_repo.list_personas(episode_id)
    plan = ep_repo.get_latest_plan(episode_id)
    takeaway = ((plan["plan_json"].get("ending") or {}).get("takeaway")
                if plan else "") or ""
    claims_by_id = {str(c["id"]): c["claim_text"]
                    for c in claims_repo.list_claims_for_project(str(episode["project_id"]))}
    themes: List[str] = []
    for src in sources_repo.list_sources(str(episode["project_id"])):
        for t in ((src.get("metadata") or {}).get("themes") or []):
            if t not in themes:
                themes.append(t)

    # segment views with evidence + best-available duration
    segments = []
    for s in scripts_repo.list_segments(version_id):
        ev = [{"type": e["evidence_type"],
               "claim_id": str(e["source_claim_id"]) if e["source_claim_id"] else None,
               "concept": e["concept"]} for e in scripts_repo.list_evidence(str(s["id"]))]
        a = audio_repo.latest_segment_audio(str(s["id"]))
        segments.append({"segment_index": s["segment_index"],
                         "speaker_label": s["speaker_label"], "text": s["text"],
                         "evidence": ev,
                         "duration_ms": a["duration_ms"] if a else (s["estimated_seconds"] or 1) * 1000})
    _tick(progress, 0.4)

    transcript = builder.transcript_md(episode, segments)
    srt = builder.transcript_srt(segments)
    notes = builder.show_notes_md(episode, themes, takeaway, participants)
    evidence = builder.evidence_report(episode, segments, claims_by_id)

    files = {
        "transcript.md": transcript.encode("utf-8"),
        "transcript.srt": srt.encode("utf-8"),
        "show_notes.md": notes.encode("utf-8"),
        "evidence_report.json": json.dumps(evidence, indent=2).encode("utf-8"),
    }
    storage = get_storage()
    mix = audio_repo.get_latest_mix(episode_id)
    if mix:
        files[f"episode.{mix['format']}"] = storage.get(mix["audio_uri"])
    _tick(progress, 0.7)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    key = f"{prefix}/exports/package_v{version['version']}.zip"
    storage.put(key, buf.getvalue())

    manifest = {"files": list(files.keys()), "has_audio": mix is not None,
                "segment_count": len(segments)}
    row = exports_repo.insert_export(episode_id, version_id, key, manifest)
    ep_repo.set_episode_status(episode_id, "completed")
    _tick(progress, 0.95)
    return {"episode_id": episode_id, "export_id": str(row["id"]),
            "files": manifest["files"], "has_audio": mix is not None}
