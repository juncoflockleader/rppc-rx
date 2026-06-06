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


# --- Episodes ---------------------------------------------------------------

class EpisodePersonaIn(BaseModel):
    persona_id: str
    version: str = "v1.0"
    role: str = "guest"            # host | guest | student | critic
    speaker_label: str             # HOST | LAOZI | BUDDHA ...


class CreateEpisodeRequest(BaseModel):
    title: Optional[str] = None
    goal: Optional[str] = None
    target_language: str = "en"
    target_duration_seconds: int = Field(default=600, ge=120, le=1800)
    format: str = "philosophical_dialogue"
    audience: Optional[str] = None
    style: Optional[str] = None
    personas: list[EpisodePersonaIn] = Field(min_length=2, max_length=3)


class EpisodeOut(BaseModel):
    id: str
    project_id: str
    title: Optional[str] = None
    status: str
    target_language: str
    target_duration_seconds: int
    format: str
    participants: list[dict] = []

    @classmethod
    def from_row(cls, row: dict, participants: Optional[list] = None) -> "EpisodeOut":
        return cls(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            title=row.get("title"),
            status=row["status"],
            target_language=row["target_language"],
            target_duration_seconds=row["target_duration_seconds"],
            format=row["format"],
            participants=participants or [],
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
