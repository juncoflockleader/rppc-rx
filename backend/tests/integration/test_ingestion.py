"""M2 ingestion pipeline against a real Postgres + pgvector, on fake providers.

text source -> process -> chunks + claims + embeddings persisted, summary API.
"""
import time

import pytest

pytestmark = pytest.mark.integration

ESSAY = (
    "Modern desire is intensified by social comparison. " * 40
    + "\n\n"
    + "When people measure themselves against others, craving grows. " * 40
)


def _wait(client, auth, job_id, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/jobs/{job_id}", headers=auth).json()
        if body["status"] in ("completed", "failed", "canceled"):
            return body
        time.sleep(0.2)
    raise AssertionError("ingestion job did not finish")


def test_ingestion_produces_chunks_claims_embeddings(client, auth):
    pid = client.post("/api/projects", json={"title": "Desire"}, headers=auth).json()["id"]
    sid = client.post(f"/api/projects/{pid}/sources/text",
                      json={"title": "Essay", "text": ESSAY}, headers=auth).json()["id"]

    job_id = client.post(f"/api/projects/{pid}/sources/{sid}/process",
                         headers=auth).json()["job_id"]
    done = _wait(client, auth, job_id)
    assert done["status"] == "completed", done

    from app.repositories import chunks as chunks_repo
    from app.repositories import claims as claims_repo

    chunk_rows = chunks_repo.list_chunks(sid)
    assert len(chunk_rows) >= 1
    # embeddings were written
    assert all(r["embedding_id"] is not None for r in chunk_rows)
    # claims were extracted and linked
    claim_rows = claims_repo.list_claims(sid)
    assert len(claim_rows) >= 1

    # vector retrieval returns rows for a query embedding
    from app.providers.embeddings import get_embedding_provider
    qvec = get_embedding_provider().embed(["desire and comparison"])[0]
    hits = chunks_repo.search_project(pid, qvec, k=3)
    assert len(hits) >= 1
    assert "score" in hits[0]


def test_summary_endpoint_returns_themes_and_claims(client, auth):
    pid = client.post("/api/projects", json={"title": "Desire2"}, headers=auth).json()["id"]
    sid = client.post(f"/api/projects/{pid}/sources/text",
                      json={"text": ESSAY}, headers=auth).json()["id"]
    job_id = client.post(f"/api/projects/{pid}/sources/{sid}/process",
                         headers=auth).json()["job_id"]
    _wait(client, auth, job_id)

    r = client.get(f"/api/sources/{sid}/summary", headers=auth)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "processed"
    assert body["summary"]
    assert isinstance(body["themes"], list) and body["themes"]
    assert len(body["claims"]) >= 1


def test_summary_requires_ownership(client, auth):
    # unknown source -> 404
    import uuid
    r = client.get(f"/api/sources/{uuid.uuid4()}/summary", headers=auth)
    assert r.status_code == 404
