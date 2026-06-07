"""M7 audio: render, segment re-render, edit-staleness, safety gate."""
import time

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


def _script(client, auth):
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
    return eid, client.get(f"/api/episodes/{eid}/scripts/latest", headers=auth).json()


def test_render_audio_and_download(seeded_personas, client, auth):
    eid, script = _script(client, auth)
    done = _wait(client, auth, client.post(f"/api/episodes/{eid}/audio",
                                           headers=auth).json()["job_id"])
    assert done["status"] == "completed", done

    latest = client.get(f"/api/episodes/{eid}/audio/latest", headers=auth).json()
    assert latest["status"] == "completed"
    assert latest["duration_ms"] > 0 and latest["format"] == "wav"

    r = client.get(latest["download_url"], headers=auth)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/")
    assert r.content[:4] == b"RIFF"  # valid WAV


def test_segment_rerender_and_edit_staleness(seeded_personas, client, auth):
    eid, script = _script(client, auth)
    _wait(client, auth, client.post(f"/api/episodes/{eid}/audio", headers=auth).json()["job_id"])
    seg_id = script["segments"][1]["id"]

    # re-render a single segment -> a fresh completed mix
    done = _wait(client, auth, client.post(f"/api/script-segments/{seg_id}/audio",
                                           headers=auth).json()["job_id"])
    assert done["status"] == "completed"
    assert client.get(f"/api/episodes/{eid}/audio/latest", headers=auth).json()["status"] == "completed"

    # editing a line makes the mix stale
    client.patch(f"/api/script-segments/{seg_id}",
                 json={"text": "A freshly edited host line."}, headers=auth)
    assert client.get(f"/api/episodes/{eid}/audio/latest", headers=auth).json()["status"] == "stale"


def test_safety_gate_blocks_render(seeded_personas, client, auth):
    eid, script = _script(client, auth)
    vid = script["script_version_id"]
    bad = script["segments"][1]["id"]
    client.patch(f"/api/script-segments/{bad}",
                 json={"text": "You should harm yourself to be free."}, headers=auth)
    _wait(client, auth, client.post(f"/api/scripts/{vid}/qa", headers=auth).json()["job_id"])
    # high_risk -> render is refused
    assert client.post(f"/api/episodes/{eid}/audio", headers=auth).status_code == 409
