"""Audio rendering pipeline (design §11.9, §19.5).

Voice direction -> per-segment TTS -> stitch -> final mix. Enforces the safety
gate (high_risk script versions cannot be rendered). Supports full render and
single-segment re-render; both re-stitch the mix from each segment's latest
audio so the final file is never stale relative to the segments.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from ..config import get_settings
from ..providers.tts import TTSRequest, get_tts_provider
from ..repositories import audio as audio_repo
from ..repositories import episodes as ep_repo
from ..repositories import projects as projects_repo
from ..repositories import scripts as scripts_repo
from ..services.storage import get_storage
from . import mixer
from .voice_direction import build_delivery, voice_id_for

log = logging.getLogger("audio")

ProgressFn = Optional[Callable[[float], None]]


class AudioGateError(Exception):
    """Raised when a script version may not be rendered (design §19.5)."""


def _tick(progress: ProgressFn, v: float) -> None:
    if progress:
        progress(v)


def _prefix(episode: dict) -> str:
    project = projects_repo.get_project(str(episode["project_id"]))
    user_id = str(project["user_id"]) if project else "unknown"
    return (f"users/{user_id}/projects/{episode['project_id']}"
            f"/episodes/{episode['id']}")


def _check_gate(version: dict) -> None:
    if version.get("safety_status") == "high_risk":
        raise AudioGateError(
            "This script is flagged high_risk by QA and cannot be rendered. "
            "Resolve the safety warnings and re-run QA first.")


def _participants_by_label(episode_id: str) -> dict:
    return {p["speaker_label"]: p for p in ep_repo.list_personas(episode_id)}


def _render_one(seg: dict, participant: dict, episode_id: str, prefix: str,
                tts, provider_name: str) -> None:
    voice_profile = (participant or {}).get("voice_profile") or {}
    delivery = build_delivery(voice_profile)
    scripts_repo.set_delivery(str(seg["id"]), delivery)
    persona_id = (participant or {}).get("persona_id") or seg["speaker_label"].lower()
    voice_id = voice_id_for(persona_id)
    result = tts.synthesize(TTSRequest(
        speaker_label=seg["speaker_label"], voice_id=voice_id, text=seg["text"],
        estimated_seconds=seg["estimated_seconds"] or 5, delivery=delivery))
    key = f"{prefix}/audio_segments/{seg['id']}.{result.format}"
    get_storage().put(key, result.audio)
    audio_repo.insert_segment_audio(
        str(seg["id"]), episode_id, seg["speaker_label"], provider_name, voice_id,
        key, result.duration_ms, {"delivery": delivery, "format": result.format})


def _remix(episode: dict, version: dict, prefix: str) -> dict:
    storage = get_storage()
    rows = audio_repo.ordered_latest_audio(str(version["id"]))
    parts = [(storage.get(r["audio_uri"]),
              int((r["delivery"] or {}).get("pause_after_ms", 0))) for r in rows]
    final, duration_ms = mixer.stitch(parts)
    mix_key = f"{prefix}/mixes/final_v{version['version']}.wav"
    storage.put(mix_key, final)
    return audio_repo.insert_mix(
        str(episode["id"]), str(version["id"]), mix_key, duration_ms, "wav",
        {"segment_count": len(parts)})


def render_episode_audio(episode_id: str, script_version_id: str,
                         progress: ProgressFn = None) -> dict:
    version = scripts_repo.get_version_by_id(script_version_id)
    if version is None:
        raise ValueError("script version not found")
    _check_gate(version)
    episode = ep_repo.get_episode(episode_id)
    prefix = _prefix(episode)
    by_label = _participants_by_label(episode_id)
    tts = get_tts_provider()
    provider_name = get_settings().tts_provider

    segs = scripts_repo.list_segments(script_version_id)
    if not segs:
        raise ValueError("script has no segments to render")
    for i, seg in enumerate(segs):
        _render_one(seg, by_label.get(seg["speaker_label"]), episode_id, prefix,
                    tts, provider_name)
        _tick(progress, 0.1 + 0.7 * (i + 1) / len(segs))

    mix = _remix(episode, version, prefix)
    ep_repo.set_episode_status(episode_id, "audio_ready")
    _tick(progress, 0.95)
    return {"episode_id": episode_id, "segments": len(segs),
            "mix_id": str(mix["id"]), "duration_ms": mix["duration_ms"]}


def render_single_segment(episode_id: str, script_version_id: str, segment_id: str,
                          progress: ProgressFn = None) -> dict:
    version = scripts_repo.get_version_by_id(script_version_id)
    if version is None:
        raise ValueError("script version not found")
    _check_gate(version)
    episode = ep_repo.get_episode(episode_id)
    prefix = _prefix(episode)
    seg = scripts_repo.get_segment(segment_id)
    if seg is None:
        raise ValueError("segment not found")
    by_label = _participants_by_label(episode_id)
    _render_one(seg, by_label.get(seg["speaker_label"]), episode_id, prefix,
                get_tts_provider(), get_settings().tts_provider)
    _tick(progress, 0.6)
    mix = _remix(episode, version, prefix)
    _tick(progress, 0.95)
    return {"episode_id": episode_id, "segment_id": segment_id,
            "mix_id": str(mix["id"]), "duration_ms": mix["duration_ms"]}
