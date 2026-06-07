"""Script QA pipeline (design §11.6-11.7, §19.5).

Runs all QA dimensions over a script version, persists a qa_report per
dimension, attaches warnings to segments, rolls up a qa_summary, and sets the
safety gate (safety_status). High-severity findings mark segments needs_review.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from ..providers.embeddings import get_embedding_provider
from ..providers.llm import get_llm_provider
from ..repositories import claims as claims_repo
from ..repositories import episodes as ep_repo
from ..repositories import qa as qa_repo
from ..repositories import scripts as scripts_repo
from . import checks, llm_checks

log = logging.getLogger("qa")

ProgressFn = Optional[Callable[[float], None]]


def _tick(progress: ProgressFn, v: float) -> None:
    if progress:
        progress(v)


def run_qa(script_version_id: str, progress: ProgressFn = None) -> dict:
    version = scripts_repo.get_version_by_id(script_version_id)
    if version is None:
        raise ValueError("script version not found")
    episode_id = str(version["episode_id"])
    episode = ep_repo.get_episode(episode_id)

    participants = ep_repo.list_personas(episode_id)
    role_by_label = {p["speaker_label"]: p["role"] for p in participants}

    rows = scripts_repo.list_segments(script_version_id)
    segs: List[Dict] = []
    index_to_id: Dict[int, str] = {}
    for r in rows:
        ev = [{"type": e["evidence_type"],
               "claim_id": str(e["source_claim_id"]) if e["source_claim_id"] else None}
              for e in scripts_repo.list_evidence(str(r["id"]))]
        view = {"id": str(r["id"]), "segment_index": r["segment_index"],
                "speaker_label": r["speaker_label"],
                "role": role_by_label.get(r["speaker_label"], "guest"),
                "text": r["text"], "evidence": ev}
        segs.append(view)
        index_to_id[r["segment_index"]] = str(r["id"])

    claims_by_id = {str(c["id"]): c["claim_text"]
                    for c in claims_repo.list_claims_for_project(str(episode["project_id"]))}

    provider = get_llm_provider()
    embedder = get_embedding_provider()

    # --- run dimensions ---
    grounding = llm_checks.source_grounding(provider, segs, claims_by_id)
    _tick(progress, 0.3)
    fidelity = llm_checks.persona_fidelity(provider, segs, participants)
    _tick(progress, 0.5)
    anach_score, anach_w = checks.anachronism_check(segs)
    safety_score, safety_w, high_risk = checks.safety_check(segs)
    dialog_score, dialog_w = checks.dialogue_quality_check(segs)
    audio_score, audio_w = checks.audio_readiness_check(segs)
    distinct_score, distinct_w = checks.distinctiveness_check(segs, embedder)
    _tick(progress, 0.75)

    def _attach_ids(warnings: List[dict]) -> List[dict]:
        out = []
        for w in warnings:
            if "segment_id" not in w and "segment_index" in w:
                w = {**w, "segment_id": index_to_id.get(w["segment_index"])}
            out.append(w)
        return out

    grounding_w = _attach_ids(grounding.get("warnings", []))
    fidelity_w = _attach_ids(fidelity.get("warnings", []))

    # --- persist per-dimension reports ---
    reports = {
        "source_grounding": ({"score": grounding.get("score", 1.0)}, grounding_w),
        "persona_fidelity": ({"persona_scores": fidelity.get("persona_scores", {}),
                              "distinctiveness_score": fidelity.get("distinctiveness_score")},
                             fidelity_w),
        "anachronism": ({"score": anach_score}, anach_w),
        "safety": ({"score": safety_score, "high_risk": high_risk}, safety_w),
        "dialogue_quality": ({"score": dialog_score}, dialog_w),
        "audio_readiness": ({"score": audio_score}, audio_w),
        "distinctiveness": ({"score": distinct_score}, distinct_w),
    }
    for rtype, (score_json, warnings) in reports.items():
        qa_repo.insert_report(episode_id, script_version_id, rtype, score_json, warnings)

    # --- attach warnings to segments + flag needs_review ---
    by_segment: Dict[str, List[dict]] = defaultdict(list)
    all_warnings: List[dict] = []
    for _rtype, (_s, warnings) in reports.items():
        for w in warnings:
            all_warnings.append(w)
            if w.get("segment_id"):
                by_segment[w["segment_id"]].append(
                    {"severity": w["severity"], "message": w["message"],
                     "suggested_action": w.get("suggested_action"),
                     "suggested_rewrite": w.get("suggested_rewrite")})
    for seg in segs:
        seg_warnings = by_segment.get(seg["id"], [])
        has_high = any(w["severity"] == "high" for w in seg_warnings)
        scripts_repo.update_segment_qa(
            seg["id"], {"warnings": seg_warnings},
            status="needs_review" if has_high else None)

    # --- rollup + safety gate (§19.5) ---
    high_count = sum(1 for w in all_warnings if w["severity"] == "high")
    persona_scores = fidelity.get("persona_scores", {})
    avg_fidelity = round(sum(persona_scores.values()) / len(persona_scores), 3) \
        if persona_scores else None
    safety_high = high_risk or any(w["severity"] == "high" for w in safety_w)
    if safety_high:
        safety_status = "high_risk"
    elif high_count:
        safety_status = "needs_review"
    else:
        safety_status = "ok"

    qa_summary = {
        "source_grounding_score": grounding.get("score", 1.0),
        "persona_fidelity_score": avg_fidelity,
        "distinctiveness_score": distinct_score,
        "anachronism_score": anach_score,
        "safety_score": safety_score,
        "dialogue_quality_score": dialog_score,
        "audio_readiness_score": audio_score,
        "high_severity_warning_count": high_count,
        "total_warning_count": len(all_warnings),
        "total_segments": len(segs),
    }
    scripts_repo.set_version_qa(script_version_id, qa_summary, safety_status)
    ep_repo.set_episode_status(episode_id, "qa_complete")
    _tick(progress, 0.95)
    return {"script_version_id": script_version_id, "safety_status": safety_status,
            "summary": qa_summary}
