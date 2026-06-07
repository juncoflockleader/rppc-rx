"""Script generation pipeline (design §11.5, §27).

discussion plan + role context cards + source claims -> segment-level script with
evidence links. Segments are stored individually (design §4.2) so they can be
edited, rewritten, QA'd, and re-rendered independently.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from ..providers.llm import get_llm_provider
from ..repositories import claims as claims_repo
from ..repositories import episodes as ep_repo
from ..repositories import scripts as scripts_repo
from . import generator
from .estimate import estimate_seconds

log = logging.getLogger("scripting")

ProgressFn = Optional[Callable[[float], None]]


def _tick(progress: ProgressFn, value: float) -> None:
    if progress:
        progress(value)


def generate_script(episode_id: str, progress: ProgressFn = None) -> dict:
    episode = ep_repo.get_episode(episode_id)
    if episode is None:
        raise ValueError(f"episode {episode_id} not found")
    plan_row = ep_repo.get_latest_plan(episode_id)
    if plan_row is None:
        raise ValueError("episode has no discussion plan; generate the plan first")

    participants = ep_repo.list_personas(episode_id)
    label_to_version = {p["speaker_label"]: str(p["persona_version_id"]) for p in participants}
    label_to_role = {p["speaker_label"]: p["role"] for p in participants}
    host_label = next((p["speaker_label"] for p in participants if p["role"] == "host"),
                      participants[0]["speaker_label"])

    cards = [dict(c["card_json"], speaker_label=c["speaker_label"])
             for c in ep_repo.latest_cards(episode_id)]
    source_claims = claims_repo.list_claims_for_project(str(episode["project_id"]))
    valid_claim_ids = {str(c["id"]) for c in source_claims}

    provider = get_llm_provider()
    _tick(progress, 0.15)
    script = generator.build_script(
        provider, episode, plan_row["plan_json"], cards, source_claims, host_label)
    _tick(progress, 0.6)

    version = scripts_repo.create_version(episode_id, str(plan_row["id"]))
    version_id = str(version["id"])

    total_seconds = 0
    words_by_speaker: Dict[str, int] = defaultdict(int)
    segments = sorted(script["segments"], key=lambda s: s["segment_index"])
    for i, seg in enumerate(segments, start=1):
        label = seg["speaker_label"]
        role = label_to_role.get(label, "guest")
        secs = estimate_seconds(seg["text"], role)
        total_seconds += secs
        words_by_speaker[label] += len(seg["text"].split())
        row = scripts_repo.insert_segment(
            script_version_id=version_id, episode_id=episode_id, segment_index=i,
            beat_id=seg.get("beat_id"),
            speaker_persona_version_id=label_to_version.get(label),
            speaker_label=label, text=seg["text"], estimated_seconds=secs,
        )
        _persist_evidence(str(row["id"]), seg.get("evidence", []), valid_claim_ids)

    total_words = sum(words_by_speaker.values()) or 1
    speaker_share = {k: round(v / total_words, 3) for k, v in words_by_speaker.items()}
    scripts_repo.set_total(version_id, total_seconds,
                           {"speaker_share": speaker_share, "segment_count": len(segments)})
    ep_repo.set_episode_status(episode_id, "script_ready")
    _tick(progress, 0.95)
    return {"episode_id": episode_id, "script_version": version["version"],
            "segments": len(segments), "total_estimated_seconds": total_seconds,
            "speaker_share": speaker_share}


def _persist_evidence(segment_id: str, evidence: List[dict], valid_claim_ids: set) -> None:
    for ev in evidence:
        etype = ev.get("type")
        claim_id = ev.get("claim_id")
        # A source_material link must point at a real claim, else it's unsupported.
        if etype == "source_material":
            if claim_id in valid_claim_ids:
                scripts_repo.insert_evidence(segment_id, "source_material",
                                             source_claim_id=claim_id)
            else:
                scripts_repo.insert_evidence(
                    segment_id, "unsupported_or_needs_review",
                    notes=f"claimed source_material with unknown claim_id={claim_id}")
        elif etype == "persona_canon":
            scripts_repo.insert_evidence(segment_id, "persona_canon",
                                         concept=ev.get("concept"))
        else:
            scripts_repo.insert_evidence(segment_id, etype or "unsupported_or_needs_review",
                                         notes=ev.get("notes"))
