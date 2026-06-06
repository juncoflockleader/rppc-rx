"""Source routes (design §12.2). M1: text paste + file upload + process trigger."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..auth import require_project_owner
from ..repositories import sources as sources_repo
from ..schemas import CreateTextSourceRequest, SourceOut
from ..services.queue import get_queue
from ..services.storage import get_storage, source_key

router = APIRouter(prefix="/api/projects/{project_id}/sources", tags=["sources"])

_ALLOWED_UPLOAD = {
    "text/plain": "txt",
    "text/markdown": "md",
    "application/pdf": "pdf",
    "application/octet-stream": "txt",  # browsers sometimes send .md/.txt as this
}


@router.post("/text", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def create_text_source(body: CreateTextSourceRequest,
                       project: dict = Depends(require_project_owner)):
    storage = get_storage()
    src = sources_repo.create_source(
        project_id=str(project["id"]), type_="text_paste",
        title=body.title, original_filename=None, object_storage_uri=None,
        status="uploaded",
    )
    key = source_key(str(project["user_id"]), str(project["id"]), str(src["id"]), "original.txt")
    uri = storage.put(key, body.text.encode("utf-8"))
    sources_repo.set_source_status(str(src["id"]), "uploaded")
    # store uri
    with_uri = sources_repo.get_source(str(src["id"]))
    return SourceOut.from_row(with_uri or src)


@router.post("", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
async def upload_source(project: dict = Depends(require_project_owner),
                        file: UploadFile = File(...)):
    type_ = _ALLOWED_UPLOAD.get(file.content_type or "", None)
    if type_ is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Only .txt, .md, and .pdf uploads are supported in the MVP.",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty.")

    storage = get_storage()
    src = sources_repo.create_source(
        project_id=str(project["id"]), type_=type_, title=file.filename,
        original_filename=file.filename, object_storage_uri=None, status="uploaded",
    )
    key = source_key(str(project["user_id"]), str(project["id"]),
                     str(src["id"]), file.filename or f"original.{type_}")
    storage.put(key, data)
    return SourceOut.from_row(src)


@router.get("", response_model=list[SourceOut])
def list_sources(project: dict = Depends(require_project_owner)):
    return [SourceOut.from_row(r) for r in sources_repo.list_sources(str(project["id"]))]


@router.post("/{source_id}/process", status_code=status.HTTP_202_ACCEPTED)
def process_source(source_id: str, project: dict = Depends(require_project_owner)):
    src = sources_repo.get_source(source_id)
    if src is None or str(src["project_id"]) != str(project["id"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")
    sources_repo.set_source_status(source_id, "parsing")
    job = get_queue().enqueue(
        "source_ingestion", {"source_id": source_id}, project_id=str(project["id"]),
    )
    return {"job_id": str(job["id"]), "status": "queued"}
