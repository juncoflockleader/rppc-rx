"""Job progress routes (design §12.7).

GET /api/jobs/{id}          -> current job state
GET /api/jobs/{id}/events   -> Server-Sent Events stream of progress
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ..auth import get_current_user
from ..repositories import jobs as jobs_repo
from ..schemas import JobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_TERMINAL = {"completed", "failed", "canceled"}


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, _user: dict = Depends(get_current_user)):
    row = jobs_repo.get_job(job_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found.")
    return JobOut.from_row(row)


@router.get("/{job_id}/events")
async def job_events(job_id: str, _user: dict = Depends(get_current_user)):
    if jobs_repo.get_job(job_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found.")

    async def stream():
        last = None
        while True:
            row = jobs_repo.get_job(job_id)
            if row is None:
                break
            snapshot = (row["status"], float(row["progress"]))
            if snapshot != last:
                last = snapshot
                payload = {"progress": float(row["progress"]),
                           "status": row["status"],
                           "message": _message_for(row)}
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
            if row["status"] in _TERMINAL:
                done = {"job_id": job_id, "status": row["status"],
                        "output": row.get("output_json"), "error": row.get("error_json")}
                yield f"event: completed\ndata: {json.dumps(done)}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream")


def _message_for(row: dict) -> str:
    return {
        "queued": "Queued",
        "running": f"Working on {row['job_type']}",
        "completed": "Done",
        "failed": "Failed",
        "canceled": "Canceled",
    }.get(row["status"], row["status"])
