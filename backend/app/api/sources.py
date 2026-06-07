"""Source routes (design §12.2). M1: text paste + file upload + process trigger."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..auth import require_project_owner
from ..config import get_settings
from ..observability import emit
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


def _check_size(n_bytes: int) -> None:
    limit = get_settings().max_source_bytes
    if n_bytes > limit:
        raise HTTPException(
            getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
            f"Source is too large ({n_bytes} bytes). The limit is {limit} bytes; "
            "please split it into smaller sources.",
        )


@router.post("/text", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def create_text_source(body: CreateTextSourceRequest,
                       project: dict = Depends(require_project_owner)):
    data = body.text.encode("utf-8")
    _check_size(len(data))

    storage = get_storage()
    src = sources_repo.create_source(
        project_id=str(project["id"]), type_="text_paste",
        title=body.title, original_filename=None, object_storage_uri=None,
        status="uploaded",
    )
    key = source_key(str(project["user_id"]), str(project["id"]), str(src["id"]), "original.txt")
    uri = storage.put(key, data)
    sources_repo.set_object_storage_uri(str(src["id"]), uri)  # persist the storage uri
    emit("source_uploaded", project_id=str(project["id"]), source_id=str(src["id"]),
         type="text_paste", bytes=len(data))

    return SourceOut.from_row(sources_repo.get_source(str(src["id"])) or src)


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
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty.")
    _check_size(len(data))

    storage = get_storage()
    src = sources_repo.create_source(
        project_id=str(project["id"]), type_=type_, title=file.filename,
        original_filename=file.filename, object_storage_uri=None, status="uploaded",
    )
    key = source_key(str(project["user_id"]), str(project["id"]),
                     str(src["id"]), file.filename or f"original.{type_}")
    uri = storage.put(key, data)
    sources_repo.set_object_storage_uri(str(src["id"]), uri)  # persist the storage uri
    emit("source_uploaded", project_id=str(project["id"]), source_id=str(src["id"]),
         type=type_, bytes=len(data))

    return SourceOut.from_row(sources_repo.get_source(str(src["id"])) or src)


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
