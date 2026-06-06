"""Worker entrypoint (design §6.9).

Usage:
  JOB_QUEUE_BACKEND=rq python -m app.workers.worker     # consume the Redis queue
  python -m app.workers.worker                          # inproc note (no-op consumer)

With the default `inproc` backend, jobs run inside the API process on a thread
pool, so a separate worker is not required for local demos. This entrypoint is
the seam for moving execution off-process (RQ today; Celery/Dramatiq later).
"""
from __future__ import annotations

import sys

from ..config import get_settings
# Importing handlers registers every job_type in the queue's registry.
from . import handlers  # noqa: F401


def main() -> int:
    settings = get_settings()
    if settings.job_queue_backend == "rq":
        from redis import Redis
        from rq import Queue, Worker

        conn = Redis.from_url(settings.redis_url)
        print("Starting RQ worker on queue 'default' ...")
        Worker([Queue("default", connection=conn)], connection=conn).work()
        return 0

    print(
        "JOB_QUEUE_BACKEND=inproc: jobs execute inside the API process on a "
        "background thread pool. No separate worker needed for local demos.\n"
        "Set JOB_QUEUE_BACKEND=rq (and `pip install -e .[queue]`) to run "
        "off-process workers."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
