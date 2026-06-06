"""Source ingestion pipeline (design §11.1).

parse -> chunk -> store chunks -> summary -> claims -> embeddings -> processed.

Run as one orchestrating job for the MVP. Each step is a standalone function so
it can later split into separate queue jobs (§17.2) with per-stage retries
without rewriting the logic. `progress` is an optional callback (0..1).
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from ..providers.embeddings import get_embedding_provider
from ..providers.llm import get_llm_provider
from ..repositories import chunks as chunks_repo
from ..repositories import claims as claims_repo
from ..repositories import sources as sources_repo
from ..services.storage import get_storage
from . import analysis
from .chunker import chunk_document
from .parser import parse

log = logging.getLogger("ingestion")

ProgressFn = Optional[Callable[[float], None]]


def _tick(progress: ProgressFn, value: float) -> None:
    if progress:
        progress(value)


def ingest_source(source_id: str, progress: ProgressFn = None) -> dict:
    src = sources_repo.get_source(source_id)
    if src is None:
        raise ValueError(f"source {source_id} not found")
    project_id = str(src["project_id"])

    # 1. Load original bytes from object storage.
    if not src.get("object_storage_uri"):
        raise ValueError("source has no stored content to parse")
    key = src["object_storage_uri"].split("://", 1)[-1]
    # The local backend's uri is file://<abs path>; map back to a storage key.
    storage = get_storage()
    data = _read_original(storage, src)

    # 2. Parse -> 3. chunk.
    doc = parse(src["type"], data)
    _tick(progress, 0.2)
    chunk_objs = [c.__dict__ for c in chunk_document(doc)]
    if not chunk_objs:
        raise ValueError("parsing produced no chunks")

    # 4. Persist chunks.
    rows = chunks_repo.insert_chunks(source_id, project_id, chunk_objs)
    chunk_id_by_index = {r["chunk_index"]: str(r["id"]) for r in rows}
    _tick(progress, 0.4)

    provider = get_llm_provider()

    # 5. Summary + themes.
    summary = analysis.summarize(provider, doc.text)
    sources_repo.set_summary(source_id, summary["summary"], summary.get("themes", []))
    _tick(progress, 0.6)

    # 6. Claims.
    claims = analysis.extract_claims(provider, chunk_objs)
    claim_rows = claims_repo.insert_claims(
        source_id, project_id, claims["claims"], chunk_id_by_index
    )
    _tick(progress, 0.8)

    # 7. Embeddings (project_source index).
    embedder = get_embedding_provider()
    vectors = embedder.embed([r["text"] for r in rows])
    for r, vec in zip(rows, vectors):
        chunks_repo.set_embedding(str(r["id"]), vec)
    _tick(progress, 0.95)

    sources_repo.set_source_status(source_id, "processed")
    return {
        "source_id": source_id,
        "chunks": len(rows),
        "claims": len(claim_rows),
        "themes": summary.get("themes", []),
    }


def _read_original(storage, src: dict) -> bytes:
    """Read the stored original. For the local backend the uri encodes the abs
    path; reconstruct the storage key from it."""
    uri = src["object_storage_uri"]
    # uri = file://<LOCAL_STORAGE_ROOT>/<key>
    from ..config import get_settings

    root = get_settings().local_storage_root
    import os

    abs_root = os.path.abspath(root)
    path = uri.split("://", 1)[-1]
    if path.startswith(abs_root):
        key = path[len(abs_root):].lstrip("/")
        return storage.get(key)
    # Fallback: read the file path directly.
    with open(path, "rb") as fh:
        return fh.read()
