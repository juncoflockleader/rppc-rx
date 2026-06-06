"""Import persona YAML seeds into the database (design §25 M3).

Reads the versioned persona YAML (authoring source of truth) and upserts
persona_assets / persona_versions, then chunks + embeds each canon doc's bundled
excerpt into the persona_canon index. Idempotent: re-running replaces a version's
canon cleanly.

Run after migrations:
    python -m app.personas_import        # or: make seed-personas
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List

from .ingestion.chunker import chunk_document
from .ingestion.parser import ParsedDoc
from .providers.embeddings import get_embedding_provider
from .repositories import personas as repo
from .services import persona_loader

_VERSION_FIELDS = ("identity_profile", "knowledge_boundary", "stance_matrix",
                   "style_profile", "forbidden_moves", "voice_profile",
                   "prompt_pack", "eval_summary")


def _import_one(persona: Dict[str, Any]) -> Dict[str, Any]:
    persona_id = persona["persona_id"]
    version = persona["version"]
    identity = persona.get("identity_profile") or {}

    repo.upsert_asset(
        asset_id=persona_id,
        display_name=persona.get("display_name", persona_id),
        type_=persona.get("type", "historical_philosophical_persona"),
        status=persona.get("status", "beta"),
        description=identity.get("summary"),
    )
    fields = {k: persona.get(k) for k in _VERSION_FIELDS}
    ver_row = repo.upsert_version(
        persona_id=persona_id,
        version=version,
        status=persona.get("status", "beta"),
        fields=fields,
        release_notes=persona.get("release_notes"),
    )
    version_id = str(ver_row["id"])

    # Rebuild canon for this version.
    repo.delete_canon_for_version(version_id)
    manifest = persona_loader.load_corpus_manifest(persona_id)
    embedder = get_embedding_provider()
    n_docs = 0
    n_chunks = 0
    for doc in manifest.get("documents", []) or []:
        seed_file = doc.get("seed_file")
        if not seed_file:
            continue  # commentary / not-yet-ingested docs are skipped in M3
        text = persona_loader.read_seed_text(persona_id, seed_file)
        parsed = ParsedDoc(text=text, page_breaks=[(0, 1)])
        chunks = chunk_document(parsed)
        if not chunks:
            continue
        doc_row = repo.insert_corpus_doc(
            persona_version_id=version_id,
            title=doc.get("title", doc.get("id", "canon")),
            source_type=doc.get("source_type"),
            text_uri=None,
            metadata={"id": doc.get("id"), "license": doc.get("license"),
                      "concepts": doc.get("concepts", [])},
        )
        vectors = embedder.embed([c.text for c in chunks])
        for c, vec in zip(chunks, vectors):
            repo.insert_canon_chunk(
                persona_version_id=version_id,
                corpus_doc_id=str(doc_row["id"]),
                chunk_index=c.chunk_index,
                text=c.text,
                token_count=c.token_count,
                concepts=doc.get("concepts", []),
                vector=vec,
            )
            n_chunks += 1
        n_docs += 1

    return {"persona_id": persona_id, "version": version,
            "canon_docs": n_docs, "canon_chunks": n_chunks}


def import_personas() -> List[Dict[str, Any]]:
    results = []
    for persona in persona_loader.load_personas():
        results.append(_import_one(persona))
    return results


def main() -> int:
    for r in import_personas():
        print(f"imported {r['persona_id']} {r['version']}: "
              f"{r['canon_docs']} canon docs, {r['canon_chunks']} chunks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
