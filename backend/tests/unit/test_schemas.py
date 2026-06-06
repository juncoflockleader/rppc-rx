import pytest
from pydantic import ValidationError

from app.schemas import (CreateProjectRequest, CreateTextSourceRequest, JobOut,
                         ProjectOut, SourceOut)


def test_create_project_requires_nonempty_title():
    with pytest.raises(ValidationError):
        CreateProjectRequest(title="")
    ok = CreateProjectRequest(title="Desire", description=None)
    assert ok.default_language == "en"


def test_create_text_source_requires_text():
    with pytest.raises(ValidationError):
        CreateTextSourceRequest(text="")


def test_project_out_from_row():
    row = {"id": 123, "title": "T", "description": None,
           "status": "draft", "default_language": "en"}
    out = ProjectOut.from_row(row)
    assert out.id == "123" and out.status == "draft"


def test_source_out_from_row():
    row = {"id": 1, "project_id": 2, "type": "text_paste",
           "title": "Essay", "status": "uploaded"}
    out = SourceOut.from_row(row)
    assert out.type == "text_paste" and out.project_id == "2"


def test_job_out_maps_error_and_ids():
    row = {"id": "j1", "job_type": "source_ingestion", "status": "failed",
           "progress": 0.5, "project_id": "p1", "episode_id": None,
           "error_json": {"message": "boom"}}
    out = JobOut.from_row(row)
    assert out.error == {"message": "boom"}
    assert out.episode_id is None and out.project_id == "p1"
    assert out.progress == 0.5
