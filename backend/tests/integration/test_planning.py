"""M4 episode planning end-to-end: brief -> role context cards -> discussion plan."""
import time

import pytest

pytestmark = pytest.mark.integration

ESSAY = "Modern desire is intensified by social comparison. " * 40


def _wait(client, auth, job_id, timeout=25.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/jobs/{job_id}", headers=auth).json()
        if body["status"] in ("completed", "failed", "canceled"):
            return body
        time.sleep(0.2)
    raise AssertionError("job did not finish")


def _project_with_source(client, auth):
    pid = client.post("/api/projects", json={"title": "Desire"}, headers=auth).json()["id"]
    sid = client.post(f"/api/projects/{pid}/sources/text",
                      json={"text": ESSAY}, headers=auth).json()["id"]
    job = client.post(f"/api/projects/{pid}/sources/{sid}/process", headers=auth).json()
    _wait(client, auth, job["job_id"])
    return pid


def _create_episode(client, auth, pid):
    body = {
        "title": "Desire, Suffering, and Non-Action",
        "goal": "Help listeners understand desire.",
        "target_duration_seconds": 600,
        "personas": [
            {"persona_id": "modern_host", "version": "v1.0", "role": "host", "speaker_label": "HOST"},
            {"persona_id": "laozi", "version": "v1.0", "role": "guest", "speaker_label": "LAOZI"},
            {"persona_id": "buddha", "version": "v1.0", "role": "guest", "speaker_label": "BUDDHA"},
        ],
    }
    r = client.post(f"/api/projects/{pid}/episodes", json=body, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_episode_create_and_plan(seeded_personas, client, auth):
    pid = _project_with_source(client, auth)
    eid = _create_episode(client, auth, pid)

    # generate plan (background job)
    r = client.post(f"/api/episodes/{eid}/discussion-plan", headers=auth)
    assert r.status_code == 202
    done = _wait(client, auth, r.json()["job_id"])
    assert done["status"] == "completed", done

    # role context cards: one per speaker
    rc = client.get(f"/api/episodes/{eid}/role-context", headers=auth).json()
    labels = {c["speaker_label"] for c in rc["cards"]}
    assert {"HOST", "LAOZI", "BUDDHA"} == labels

    # discussion plan
    plan = client.get(f"/api/episodes/{eid}/discussion-plan", headers=auth).json()
    beats = plan["plan"]["beats"]
    assert len(beats) >= 3
    assert beats[0]["primary_speaker"] == "HOST"

    # episode is marked planned
    assert client.get(f"/api/episodes/{eid}", headers=auth).json()["status"] == "planned"


def test_regenerate_makes_a_new_plan_version(seeded_personas, client, auth):
    pid = _project_with_source(client, auth)
    eid = _create_episode(client, auth, pid)

    j1 = client.post(f"/api/episodes/{eid}/discussion-plan", headers=auth).json()
    _wait(client, auth, j1["job_id"])
    v1 = client.get(f"/api/episodes/{eid}/discussion-plan", headers=auth).json()["version"]

    j2 = client.post(f"/api/episodes/{eid}/discussion-plan", headers=auth).json()
    _wait(client, auth, j2["job_id"])
    v2 = client.get(f"/api/episodes/{eid}/discussion-plan", headers=auth).json()["version"]
    assert v2 == v1 + 1


def test_create_rejects_missing_persona(seeded_personas, client, auth):
    pid = _project_with_source(client, auth)
    body = {
        "title": "x", "target_duration_seconds": 600,
        "personas": [
            {"persona_id": "modern_host", "role": "host", "speaker_label": "HOST"},
            {"persona_id": "aristotle", "role": "guest", "speaker_label": "ARI"},
        ],
    }
    r = client.post(f"/api/projects/{pid}/episodes", json=body, headers=auth)
    assert r.status_code == 400


def test_create_requires_single_host(seeded_personas, client, auth):
    pid = _project_with_source(client, auth)
    body = {
        "title": "x", "target_duration_seconds": 600,
        "personas": [
            {"persona_id": "laozi", "role": "guest", "speaker_label": "LAOZI"},
            {"persona_id": "buddha", "role": "guest", "speaker_label": "BUDDHA"},
        ],
    }
    r = client.post(f"/api/projects/{pid}/episodes", json=body, headers=auth)
    assert r.status_code == 400
