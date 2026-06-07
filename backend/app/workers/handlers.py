"""Job handlers.

Each pipeline job (design §17.2) is a function `handler(job_id, payload, ctx)`.
M1 ships a registry and a working `source_ingestion` stub so the queue path is
exercisable end to end. Later milestones replace the stubs with real
parsing / LLM / TTS work — the queue and progress plumbing stay the same.
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from ..observability import emit
from ..repositories import jobs as jobs_repo
from ..repositories import sources as sources_repo

Handler = Callable[[str, Dict[str, Any]], Dict[str, Any]]

_REGISTRY: Dict[str, Handler] = {}


def register(job_type: str) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        _REGISTRY[job_type] = fn
        return fn
    return deco


def get_handler(job_type: str) -> Handler:
    if job_type not in _REGISTRY:
        raise KeyError(f"no handler registered for job_type '{job_type}'")
    return _REGISTRY[job_type]


def registered_job_types() -> list[str]:
    return sorted(_REGISTRY)


# --- M1 working stub --------------------------------------------------------

@register("source_ingestion")
def source_ingestion(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Full ingestion (design §11.1): parse -> chunk -> summary -> claims -> embed.

    Implemented in app/ingestion/pipeline; this handler just wires progress and
    failure handling. On failure the source is marked failed so the UI can show
    a human-readable error (§18).
    """
    from ..ingestion.parser import ParseError
    from ..ingestion.pipeline import ingest_source

    source_id = payload["source_id"]
    try:
        result = ingest_source(source_id, progress=lambda p: jobs_repo.set_progress(job_id, p))
    except ParseError as exc:
        sources_repo.set_source_status(source_id, "failed")
        raise  # message is already user-facing
    except Exception:
        sources_repo.set_source_status(source_id, "failed")
        raise
    emit("source_processed", source_id=source_id, chunks=result["chunks"],
         claims=result["claims"])
    return result


@register("export_package")
def export_package(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Package transcript / SRT / show notes / evidence / audio into a zip (§6.8)."""
    from ..export.pipeline import build_export

    result = build_export(payload["episode_id"],
                          progress=lambda p: jobs_repo.set_progress(job_id, p))
    emit("audio_exported", episode_id=payload["episode_id"], export_id=result["export_id"])
    return result


@register("audio_render")
def audio_render(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Voice direction + TTS + mix (design §11.9). Single segment if segment_id set."""
    from ..audio.pipeline import render_episode_audio, render_single_segment

    cb = lambda p: jobs_repo.set_progress(job_id, p)  # noqa: E731
    if payload.get("segment_id"):
        result = render_single_segment(payload["episode_id"], payload["script_version_id"],
                                       payload["segment_id"], progress=cb)
        emit("segment_rerendered", episode_id=payload["episode_id"],
             segment_id=payload["segment_id"], mode="audio")
    else:
        result = render_episode_audio(payload["episode_id"], payload["script_version_id"],
                                      progress=cb)
        emit("audio_generated", episode_id=payload["episode_id"],
             duration_ms=result["duration_ms"])
    return result


@register("script_qa")
def script_qa(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run all QA dimensions over a script version (design §11.6)."""
    from ..qa.pipeline import run_qa

    result = run_qa(payload["script_version_id"],
                    progress=lambda p: jobs_repo.set_progress(job_id, p))
    emit("qa_completed", script_version_id=payload["script_version_id"],
         safety_status=result["safety_status"])
    return result


@register("episode_planning")
def episode_planning(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Role context cards + discussion plan (design §11.3-11.4)."""
    from ..planning.pipeline import plan_episode
    from ..repositories import episodes as ep_repo

    episode_id = payload["episode_id"]
    try:
        result = plan_episode(episode_id, progress=lambda p: jobs_repo.set_progress(job_id, p))
    except Exception:
        ep_repo.set_episode_status(episode_id, "failed")
        raise
    emit("discussion_plan_generated", episode_id=episode_id,
         beats=result["beats"], cards=result["cards"])
    return result


@register("script_generation")
def script_generation(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Discussion plan -> segment-level script with evidence links (design §11.5)."""
    from ..repositories import episodes as ep_repo
    from ..scripting.pipeline import generate_script

    episode_id = payload["episode_id"]
    try:
        result = generate_script(episode_id, progress=lambda p: jobs_repo.set_progress(job_id, p))
    except Exception:
        ep_repo.set_episode_status(episode_id, "failed")
        raise
    emit("script_generated", episode_id=episode_id, segments=result["segments"])
    return result


# --- Later-milestone placeholders (registered so the queue accepts them) -----

def _todo(milestone: str) -> Handler:
    def handler(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(f"job handler arrives in {milestone}")
    return handler


for _jt, _ms in {
    "claim_extraction": "M2",
    "embedding": "M2",
    "voice_direction": "M7",
    "audio_mix": "M7",
}.items():
    _REGISTRY.setdefault(_jt, _todo(_ms))
