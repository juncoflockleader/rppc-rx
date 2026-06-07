"""M8 beta polish: export package, cost logging, feedback, notices, errors."""
import io
import time
import zipfile

import pytest

pytestmark = pytest.mark.integration

ESSAY = "Modern desire is intensified by social comparison. " * 40


def _wait(client, auth, job_id, timeout=40.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/jobs/{job_id}", headers=auth).json()
        if body["status"] in ("completed", "failed", "canceled"):
            return body
        time.sleep(0.2)
    raise AssertionError("job did not finish")


def _episode_with_audio(client, auth):
    pid = client.post("/api/projects", json={"title": "Desire"}, headers=auth).json()["id"]
    sid = client.post(f"/api/projects/{pid}/sources/text",
                      json={"text": ESSAY}, headers=auth).json()["id"]
    _wait(client, auth, client.post(
        f"/api/projects/{pid}/sources/{sid}/process", headers=auth).json()["job_id"])
    eid = client.post(f"/api/projects/{pid}/episodes", json={
        "title": "Desire", "goal": "Understand desire", "target_duration_seconds": 600,
        "personas": [
            {"persona_id": "modern_host", "role": "host", "speaker_label": "HOST"},
            {"persona_id": "laozi", "role": "guest", "speaker_label": "LAOZI"},
            {"persona_id": "buddha", "role": "guest", "speaker_label": "BUDDHA"},
        ]}, headers=auth).json()["id"]
    _wait(client, auth, client.post(
        f"/api/episodes/{eid}/discussion-plan", headers=auth).json()["job_id"])
    _wait(client, auth, client.post(
        f"/api/episodes/{eid}/scripts", headers=auth).json()["job_id"])
    _wait(client, auth, client.post(f"/api/episodes/{eid}/audio", headers=auth).json()["job_id"])
    return pid, eid


def test_export_package_contains_artifacts(seeded_personas, client, auth):
    pid, eid = _episode_with_audio(client, auth)
    done = _wait(client, auth, client.post(f"/api/episodes/{eid}/export",
                                           headers=auth).json()["job_id"])
    assert done["status"] == "completed", done

    latest = client.get(f"/api/episodes/{eid}/export/latest", headers=auth).json()
    assert latest["manifest"]["has_audio"] is True

    r = client.get(latest["download_url"], headers=auth)
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = set(zf.namelist())
    assert {"transcript.md", "transcript.srt", "show_notes.md",
            "evidence_report.json"} <= names
    assert any(n.startswith("episode.") for n in names)  # audio bundled
    # disclaimer is embedded
    assert "interpretive AI-generated personas" in zf.read("transcript.md").decode()


def test_cost_logging_records_llm_usage(seeded_personas, client, auth):
    pid, eid = _episode_with_audio(client, auth)
    cost = client.get(f"/api/episodes/{eid}/cost", headers=auth).json()
    # planning + script generation made LLM calls; TTS made char/duration usage
    assert cost["llm_calls"] > 0
    assert cost["llm_input_tokens"] > 0
    assert cost["tts_calls"] > 0
    assert cost["estimated_llm_cost_usd"] >= 0


def test_feedback_and_notices(seeded_personas, client, auth):
    pid, eid = _episode_with_audio(client, auth)
    r = client.post("/api/feedback", json={
        "target_type": "episode", "target_id": eid, "feedback_type": "thumbs",
        "rating": 1, "tags": ["distinct", "grounded"], "episode_id": eid,
        "project_id": pid}, headers=auth)
    assert r.status_code == 201 and r.json()["status"] == "recorded"

    n = client.get("/api/meta/notices").json()  # public, no auth
    assert "disclaimer_en" in n and "source_copyright" in n


def test_error_envelope_shape(client):
    # missing/invalid auth returns the standard error envelope (design §18)
    r = client.get("/api/projects")
    assert r.status_code == 401
    assert r.json()["error"]["type"] == "http_error"
    assert isinstance(r.json()["error"]["message"], str)


def test_admin_usage_requires_token(seeded_personas, client, auth):
    # admin_token unset in tests -> forbidden
    assert client.get("/api/admin/usage").status_code == 403
