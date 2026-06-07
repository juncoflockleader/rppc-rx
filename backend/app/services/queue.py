"""Job queue abstraction (design §6.9, §7, §17).

Two backends behind one interface:

  * inproc  — default. Runs handlers on a background thread pool inside the API
              process. No Redis required, so the skeleton runs out of the box.
  * rq      — Redis-backed; enqueue here, consume with `python -m app.workers.worker`.
              Use this (or Celery/Dramatiq) in staging/production.

`enqueue` always first inserts a `jobs` row (source of truth for progress),
then hands the job id to the backend. Handlers update the row as they run.
"""
from __future__ import annotations

import logging
import traceback
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from ..config import get_settings
from ..repositories import jobs as jobs_repo
from ..workers.handlers import get_handler

log = logging.getLogger("queue")


def run_job(job_id: str, job_type: str, payload: Dict[str, Any]) -> None:
    """Execute one job through its handler, driving the §17.1 state machine."""
    from ..usage import using_context

    jobs_repo.mark_running(job_id)
    row = jobs_repo.get_job(job_id) or {}
    project_id = str(row["project_id"]) if row.get("project_id") else None
    episode_id = str(row["episode_id"]) if row.get("episode_id") else None
    try:
        handler = get_handler(job_type)
        with using_context(project_id, episode_id):
            output = handler(job_id, payload)
        jobs_repo.mark_completed(job_id, output)
    except Exception as exc:  # noqa: BLE001 - we persist all failures
        log.exception("job %s (%s) failed", job_id, job_type)
        jobs_repo.mark_failed(job_id, {
            "type": exc.__class__.__name__,
            "message": str(exc),
            "trace": traceback.format_exc(limit=5),
        })


class JobQueue(ABC):
    @abstractmethod
    def enqueue(self, job_type: str, payload: Dict[str, Any],
                project_id: Optional[str] = None,
                episode_id: Optional[str] = None) -> dict:
        ...


class InProcQueue(JobQueue):
    """Background-thread queue for local dev / demos."""

    def __init__(self, max_workers: int = 4) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers,
                                        thread_name_prefix="job")

    def enqueue(self, job_type, payload, project_id=None, episode_id=None) -> dict:
        job = jobs_repo.create_job(job_type, project_id, episode_id, payload)
        self._pool.submit(run_job, str(job["id"]), job_type, payload)
        return job


class RQQueue(JobQueue):
    """Redis-backed queue. Requires the `queue` extra (`pip install -e .[queue]`)."""

    def __init__(self) -> None:
        from redis import Redis  # local import keeps redis optional
        from rq import Queue

        self._q = Queue("default", connection=Redis.from_url(get_settings().redis_url))

    def enqueue(self, job_type, payload, project_id=None, episode_id=None) -> dict:
        job = jobs_repo.create_job(job_type, project_id, episode_id, payload)
        self._q.enqueue(run_job, str(job["id"]), job_type, payload)
        return job


_queue: Optional[JobQueue] = None


def get_queue() -> JobQueue:
    global _queue
    if _queue is None:
        backend = get_settings().job_queue_backend
        _queue = RQQueue() if backend == "rq" else InProcQueue()
    return _queue
