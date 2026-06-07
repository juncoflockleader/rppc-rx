"""M5 script generation + segment edit/rewrite, end to end."""
import time

import pytest

pytestmark = pytest.mark.integration

ESSAY = "Modern desire is intensified by social comparison. " * 40


def _wait(client, auth, job_id, timeout=30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/jobs/{job_id}", headers=auth).json()
        if body["status"] in ("completed", "failed", "canceled"):
            return body
        time.sleep(0.2)
    raise AssertionError("job did not finish")


def _episode_with_plan(client, auth):
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
    return eid


def test_generate_script_with_segments_and_evidence(seeded_personas, client, auth):
    eid = _episode_with_plan(client, auth)

    r = client.post(f"/api/episodes/{eid}/scripts", headers=auth)
    assert r.status_code == 202
    done = _wait(client, auth, r.json()["job_id"])
    assert done["status"] == "completed", done

    script = client.get(f"/api/episodes/{eid}/scripts/latest", headers=auth).json()
    segs = script["segments"]
    assert len(segs) >= 4
    assert script["total_estimated_seconds"] > 0
    assert "speaker_share" in script["metadata"]
    # distinct speakers and every segment has evidence
    assert {"HOST", "LAOZI", "BUDDHA"} <= {s["speaker_label"] for s in segs}
    assert all(s["evidence"] for s in segs)
    # at least one source_material link resolves to a real claim id
    src = [e for s in segs for e in s["evidence"] if e["type"] == "source_material"]
    assert src and src[0]["claim_id"]


def test_generate_requires_plan(seeded_personas, client, auth):
    pid = client.post("/api/projects", json={"title": "x"}, headers=auth).json()["id"]
    eid = client.post(f"/api/projects/{pid}/episodes", json={
        "title": "x", "target_duration_seconds": 600,
        "personas": [
            {"persona_id": "modern_host", "role": "host", "speaker_label": "HOST"},
            {"persona_id": "laozi", "role": "guest", "speaker_label": "LAOZI"},
        ]}, headers=auth).json()["id"]
    assert client.post(f"/api/episodes/{eid}/scripts", headers=auth).status_code == 409


def test_edit_and_rewrite_segment(seeded_personas, client, auth):
    eid = _episode_with_plan(client, auth)
    _wait(client, auth, client.post(f"/api/episodes/{eid}/scripts",
                                    headers=auth).json()["job_id"])
    segs = client.get(f"/api/episodes/{eid}/scripts/latest", headers=auth).json()["segments"]
    seg_id = segs[0]["id"]

    # manual edit
    r = client.patch(f"/api/script-segments/{seg_id}",
                     json={"text": "A deliberately rewritten and longer host line here."},
                     headers=auth)
    assert r.status_code == 200
    assert r.json()["status"] == "edited"
    assert r.json()["text"].startswith("A deliberately rewritten")

    # llm rewrite
    r2 = client.post(f"/api/script-segments/{seg_id}/rewrite",
                     json={"instruction": "make it warmer"}, headers=auth)
    assert r2.status_code == 200
    assert "make it warmer" in r2.json()["text"]  # deterministic fake echoes the instruction
