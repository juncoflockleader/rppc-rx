"""Request/response models (design §12). MVP subset for Milestone 1."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# --- Projects ---------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: Optional[str] = None
    default_language: str = "en"


class ProjectOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    default_language: str

    @classmethod
    def from_row(cls, row: dict) -> "ProjectOut":
        return cls(
            id=str(row["id"]),
            title=row["title"],
            description=row.get("description"),
            status=row["status"],
            default_language=row["default_language"],
        )


# --- Sources ----------------------------------------------------------------

class CreateTextSourceRequest(BaseModel):
    title: Optional[str] = None
    text: str = Field(min_length=1)


class SourceOut(BaseModel):
    id: str
    project_id: str
    type: str
    title: Optional[str] = None
    status: str

    @classmethod
    def from_row(cls, row: dict) -> "SourceOut":
        return cls(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            type=row["type"],
            title=row.get("title"),
            status=row["status"],
        )


# --- Jobs -------------------------------------------------------------------

class JobOut(BaseModel):
    id: str
    job_type: str
    status: str
    progress: float
    project_id: Optional[str] = None
    episode_id: Optional[str] = None
    error: Optional[dict] = None

    @classmethod
    def from_row(cls, row: dict) -> "JobOut":
        return cls(
            id=str(row["id"]),
            job_type=row["job_type"],
            status=row["status"],
            progress=float(row["progress"]),
            project_id=str(row["project_id"]) if row.get("project_id") else None,
            episode_id=str(row["episode_id"]) if row.get("episode_id") else None,
            error=row.get("error_json"),
        )
