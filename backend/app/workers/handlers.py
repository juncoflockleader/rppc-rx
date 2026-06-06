"""Job handlers.

Each pipeline job (design §17.2) is a function `handler(job_id, payload, ctx)`.
M1 ships a registry and a working `source_ingestion` stub so the queue path is
exercisable end to end. Later milestones replace the stubs with real
parsing / LLM / TTS work — the queue and progress plumbing stay the same.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict

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
    """Minimal ingestion: mark the source processed.

    Real implementation (M2): parse -> clean -> chunk -> summarize -> extract
    claims -> embed. Here we just walk the progress bar so the SSE/progress UI
    is demoable.
    """
    source_id = payload["source_id"]
    for step, pct in [("parsing", 0.25), ("chunking", 0.5), ("summarizing", 0.75)]:
        jobs_repo.set_progress(job_id, pct)
        time.sleep(0.2)  # simulate work
    sources_repo.set_source_status(source_id, "processed")
    return {"source_id": source_id, "note": "M1 stub — real ingestion lands in M2"}


# --- Later-milestone placeholders (registered so the queue accepts them) -----

def _todo(milestone: str) -> Handler:
    def handler(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(f"job handler arrives in {milestone}")
    return handler


for _jt, _ms in {
    "claim_extraction": "M2",
    "embedding": "M2",
    "episode_planning": "M4",
    "script_generation": "M5",
    "script_qa": "M6",
    "voice_direction": "M7",
    "audio_render": "M7",
    "audio_mix": "M7",
    "export_package": "M8",
}.items():
    _REGISTRY.setdefault(_jt, _todo(_ms))
