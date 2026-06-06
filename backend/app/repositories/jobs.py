"""Job data access (raw SQL). Backs the progress API and the job state machine
(design §17.1: queued -> running -> completed|failed|canceled)."""
from __future__ import annotations

import json
from typing import Optional

from ..db import get_conn


def create_job(job_type: str, project_id: Optional[str] = None,
               episode_id: Optional[str] = None, input_json: Optional[dict] = None) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO jobs (job_type, project_id, episode_id, input_json, status)
            VALUES (%s, %s, %s, %s, 'queued')
            RETURNING *
            """,
            (job_type, project_id, episode_id,
             json.dumps(input_json) if input_json is not None else None),
        ).fetchone()


def get_job(job_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id = %s", (job_id,)).fetchone()


def mark_running(job_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET status='running', started_at=now() WHERE id=%s",
            (job_id,),
        )


def set_progress(job_id: str, progress: float) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET progress=%s WHERE id=%s",
            (max(0.0, min(1.0, progress)), job_id),
        )


def mark_completed(job_id: str, output_json: Optional[dict] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE jobs
               SET status='completed', progress=1, completed_at=now(), output_json=%s
             WHERE id=%s
            """,
            (json.dumps(output_json) if output_json is not None else None, job_id),
        )


def mark_failed(job_id: str, error: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE jobs
               SET status='failed', completed_at=now(), error_json=%s
             WHERE id=%s
            """,
            (json.dumps(error), job_id),
        )
