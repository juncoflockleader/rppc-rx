"""Object storage abstraction (design §9).

A vendor-agnostic interface so business code never binds to a specific blob
store. The MVP ships a local-filesystem backend; swap in S3 later without
touching callers. Paths follow the design's recommended layout, e.g.
  users/{user_id}/projects/{project_id}/sources/{source_id}/original.pdf
"""
from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from ..config import get_settings


class StorageBackend(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes) -> str:
        """Store bytes at key, return a storage URI."""

    @abstractmethod
    def put_stream(self, key: str, stream: BinaryIO) -> str:
        ...

    @abstractmethod
    def get(self, key: str) -> bytes:
        ...

    @abstractmethod
    def signed_url(self, key: str) -> str:
        """Time-limited read URL (design §19.4)."""

    @abstractmethod
    def delete_prefix(self, prefix: str) -> None:
        """Delete everything under a prefix (project deletion cascade, §19.4)."""


class LocalStorage(StorageBackend):
    """Filesystem-backed store for local dev / MVP demos."""

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root)):
            raise ValueError("path traversal blocked")
        return p

    def put(self, key: str, data: bytes) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return self._uri(key)

    def put_stream(self, key: str, stream: BinaryIO) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as fh:
            shutil.copyfileobj(stream, fh)
        return self._uri(key)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def signed_url(self, key: str) -> str:
        # Local backend has no real signing; return a file URI. The API layer
        # streams bytes for local mode instead of redirecting.
        return self._uri(key)

    def delete_prefix(self, prefix: str) -> None:
        target = self._path(prefix)
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink()

    def _uri(self, key: str) -> str:
        return f"file://{self.root / key}"


def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.object_storage_backend == "local":
        return LocalStorage(settings.local_storage_root)
    # if settings.object_storage_backend == "s3": return S3Storage(...)
    raise NotImplementedError(
        f"storage backend '{settings.object_storage_backend}' not implemented yet"
    )


def source_key(user_id: str, project_id: str, source_id: str, filename: str) -> str:
    return f"users/{user_id}/projects/{project_id}/sources/{source_id}/{filename}"
