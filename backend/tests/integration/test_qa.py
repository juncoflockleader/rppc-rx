"""M6 QA: run dimensions, panel, safety gate, one-click repair."""
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


def test_qa_panel_has_all_dimensions(seeded_personas, client, auth):
    eid, script = _script(client, auth)
    vid = script["script_version_id"]

    done = _wait(client, auth, client.post(f"/api/scripts/{vid}/qa",
                                           headers=auth).json()["job_id"])
    assert done["status"] == "completed", done

    panel = client.get(f"/api/scripts/{vid}/qa", headers=auth).json()
    rtypes = {r["report_type"] for r in panel["reports"]}
    assert {"source_grounding", "persona_fidelity", "anachronism", "safety",
            "dialogue_quality", "audio_readiness", "distinctiveness"} == rtypes
    summary = panel["summary"]
    assert "distinctiveness_score" in summary
    assert summary["source_grounding_score"] is not None
    assert panel["safety_status"] in ("ok", "needs_review", "high_risk")


def test_anachronism_flags_segment_and_repair_fixes_it(seeded_personas, client, auth):
    eid, script = _script(client, auth)
    vid = script["script_version_id"]
    # Inject a modern term into a guest line.
    guest = next(s for s in script["segments"] if s["speaker_label"] == "LAOZI")
    client.patch(f"/api/script-segments/{guest['id']}",
                 json={"text": "The dopamine of endless striving never rests."}, headers=auth)

    _wait(client, auth, client.post(f"/api/scripts/{vid}/qa", headers=auth).json()["job_id"])
    panel = client.get(f"/api/scripts/{vid}/qa", headers=auth).json()

    anach = next(r for r in panel["reports"] if r["report_type"] == "anachronism")
    assert any(w["speaker_label"] == "LAOZI" for w in anach["warnings"])
    assert panel["safety_status"] == "needs_review"  # high-severity but not safety
    # the segment is now flagged needs_review
    seg = next(s for s in client.get(f"/api/episodes/{eid}/scripts/latest",
                                     headers=auth).json()["segments"] if s["id"] == guest["id"])
    assert seg["status"] == "needs_review"

    # one-click repair rewrites the flagged segment
    rep = client.post(f"/api/scripts/{vid}/repair", headers=auth).json()
    assert rep["count"] >= 1
    seg2 = next(s for s in client.get(f"/api/episodes/{eid}/scripts/latest",
                                      headers=auth).json()["segments"] if s["id"] == guest["id"])
    assert seg2["status"] == "edited" and seg2["text"].startswith("[rewritten]")


def test_safety_gate_high_risk(seeded_personas, client, auth):
    eid, script = _script(client, auth)
    vid = script["script_version_id"]
    seg = script["segments"][1]
    client.patch(f"/api/script-segments/{seg['id']}",
                 json={"text": "You should harm yourself to be free."}, headers=auth)
    _wait(client, auth, client.post(f"/api/scripts/{vid}/qa", headers=auth).json()["job_id"])
    panel = client.get(f"/api/scripts/{vid}/qa", headers=auth).json()
    assert panel["safety_status"] == "high_risk"
