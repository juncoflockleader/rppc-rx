"""End-to-end M1 path against a real Postgres (design §23.2).

create project -> paste source -> process -> job completes -> source processed,
plus auth and project-delete-cascade checks.
"""
import time

import pytest

pytestmark = pytest.mark.integration


def _wait_for_job(client, auth, job_id, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/api/jobs/{job_id}", headers=auth)
        assert r.status_code == 200, r.text
        body = r.json()
        if body["status"] in ("completed", "failed", "canceled"):
            return body
        time.sleep(0.2)
    raise AssertionError("job did not finish in time")


def test_full_source_pipeline(client, auth):
    # create project
    r = client.post("/api/projects", json={"title": "Desire"}, headers=auth)
    assert r.status_code == 201, r.text
    project_id = r.json()["id"]

    # it shows up in the list
    r = client.get("/api/projects", headers=auth)
    assert any(p["id"] == project_id for p in r.json())

    # paste a text source
    r = client.post(
        f"/api/projects/{project_id}/sources/text",
        json={"title": "Essay", "text": "Modern desire is intensified by comparison."},
        headers=auth,
    )
    assert r.status_code == 201, r.text
    source_id = r.json()["id"]
    assert r.json()["status"] == "uploaded"

    # the storage uri was persisted (the bug this milestone fixed)
    from app.repositories import sources as sources_repo
    assert sources_repo.get_source(source_id)["object_storage_uri"] is not None

    # trigger processing
    r = client.post(f"/api/projects/{project_id}/sources/{source_id}/process", headers=auth)
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]

    # job runs to completion on the inproc worker
    done = _wait_for_job(client, auth, job_id)
    assert done["status"] == "completed"

    # source is now processed
    assert sources_repo.get_source(source_id)["status"] == "processed"


def test_auth_required(client):
    assert client.get("/api/projects").status_code == 401
    bad = {"Authorization": "Bearer wrong"}
    assert client.get("/api/projects", headers=bad).status_code == 401


def test_size_limit_rejected(client, auth, monkeypatch):
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("MAX_SOURCE_BYTES", "10")
    get_settings.cache_clear()

    pid = client.post("/api/projects", json={"title": "X"}, headers=auth).json()["id"]
    r = client.post(f"/api/projects/{pid}/sources/text",
                    json={"text": "this is definitely longer than ten bytes"}, headers=auth)
    assert r.status_code == 413
    get_settings.cache_clear()


def test_project_delete_cascade(client, auth):
    pid = client.post("/api/projects", json={"title": "Gone"}, headers=auth).json()["id"]
    client.post(f"/api/projects/{pid}/sources/text", json={"text": "hi"}, headers=auth)
    assert client.delete(f"/api/projects/{pid}", headers=auth).status_code == 204
    assert client.get(f"/api/projects/{pid}", headers=auth).status_code == 404


def test_sse_emits_completed_event(client, auth):
    pid = client.post("/api/projects", json={"title": "S"}, headers=auth).json()["id"]
    sid = client.post(f"/api/projects/{pid}/sources/text",
                      json={"text": "hi"}, headers=auth).json()["id"]
    job_id = client.post(f"/api/projects/{pid}/sources/{sid}/process",
                         headers=auth).json()["job_id"]
    _wait_for_job(client, auth, job_id)  # ensure terminal before streaming

    with client.stream("GET", f"/api/jobs/{job_id}/events", headers=auth) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        saw_completed = False
        for line in resp.iter_lines():
            if "completed" in line:
                saw_completed = True
                break
        assert saw_completed
