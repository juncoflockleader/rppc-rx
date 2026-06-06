"""M3 persona asset import + canon index, against Postgres + pgvector (fake embeds)."""
import pytest

pytestmark = pytest.mark.integration


def test_import_creates_assets_versions_and_canon(seeded_personas):
    results = {r["persona_id"]: r for r in seeded_personas}
    assert {"laozi", "buddha", "modern_host"} <= set(results)
    # historical personas have canon chunks; the abstract host does not
    assert results["laozi"]["canon_chunks"] >= 1
    assert results["buddha"]["canon_chunks"] >= 1
    assert results["modern_host"]["canon_chunks"] == 0

    from app.repositories import personas as repo
    assets = repo.list_assets_with_latest()
    assert len(assets) == 3
    laozi = repo.get_version("laozi", "v1.0")
    assert laozi is not None
    # JSONB round-trips to a dict
    assert isinstance(laozi["stance_matrix"], dict)
    assert repo.count_canon_chunks(str(laozi["id"])) >= 1


def test_import_is_idempotent(seeded_personas):
    from app.personas_import import import_personas
    from app.repositories import personas as repo

    laozi = repo.get_version("laozi", "v1.0")
    before = repo.count_canon_chunks(str(laozi["id"]))
    import_personas()  # run again
    after = repo.count_canon_chunks(str(laozi["id"]))
    assert before == after  # rebuilt, not duplicated


def test_canon_retrieval_returns_rows(seeded_personas):
    from app.providers.embeddings import get_embedding_provider
    from app.repositories import personas as repo

    laozi = repo.get_version("laozi", "v1.0")
    qvec = get_embedding_provider().embed(["water and softness overcome the hard"])[0]
    hits = repo.search_canon(str(laozi["id"]), qvec, k=3)
    assert len(hits) >= 1
    assert "score" in hits[0] and hits[0]["text"]


def test_persona_api_serves_from_db(seeded_personas, client, auth):
    r = client.get("/api/personas", headers=auth)
    assert r.status_code == 200
    ids = {p["persona_id"] for p in r.json()}
    assert {"laozi", "buddha", "modern_host"} <= ids

    r = client.get("/api/personas/buddha/versions/v1.0", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "historical_philosophical_persona"
    assert "stance_matrix" in body and isinstance(body["forbidden_moves"], list)

    assert client.get("/api/personas/nobody/versions/v1.0", headers=auth).status_code == 404
