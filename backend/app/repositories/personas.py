"""Persona asset data access (raw SQL): assets, versions, corpus, canon index."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..db import get_conn


def _vec_literal(vec: List[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


# --- assets / versions ------------------------------------------------------

def upsert_asset(asset_id: str, display_name: str, type_: str, status: str,
                 description: Optional[str]) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO persona_assets (id, display_name, type, status, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                type = EXCLUDED.type,
                status = EXCLUDED.status,
                description = EXCLUDED.description,
                updated_at = now()
            RETURNING *
            """,
            (asset_id, display_name, type_, status, description),
        ).fetchone()


_VERSION_JSONB = ("identity_profile", "knowledge_boundary", "stance_matrix",
                  "style_profile", "forbidden_moves", "voice_profile", "prompt_pack",
                  "eval_summary")


def upsert_version(persona_id: str, version: str, status: str,
                   fields: Dict[str, Any], release_notes: Optional[str]) -> dict:
    cols = {k: json.dumps(fields.get(k)) for k in _VERSION_JSONB}
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO persona_versions
                (persona_id, version, status, identity_profile, knowledge_boundary,
                 stance_matrix, style_profile, forbidden_moves, voice_profile,
                 prompt_pack, eval_summary, release_notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (persona_id, version) DO UPDATE SET
                status = EXCLUDED.status,
                identity_profile = EXCLUDED.identity_profile,
                knowledge_boundary = EXCLUDED.knowledge_boundary,
                stance_matrix = EXCLUDED.stance_matrix,
                style_profile = EXCLUDED.style_profile,
                forbidden_moves = EXCLUDED.forbidden_moves,
                voice_profile = EXCLUDED.voice_profile,
                prompt_pack = EXCLUDED.prompt_pack,
                eval_summary = EXCLUDED.eval_summary,
                release_notes = EXCLUDED.release_notes
            RETURNING *
            """,
            (persona_id, version, status, cols["identity_profile"],
             cols["knowledge_boundary"], cols["stance_matrix"], cols["style_profile"],
             cols["forbidden_moves"], cols["voice_profile"], cols["prompt_pack"],
             cols["eval_summary"], release_notes),
        ).fetchone()


def list_assets_with_latest() -> List[dict]:
    """One row per asset, joined to its newest version (by created_at)."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT a.*, v.id AS version_id, v.version, v.status AS version_status,
                   v.identity_profile
              FROM persona_assets a
              JOIN LATERAL (
                    SELECT * FROM persona_versions pv
                     WHERE pv.persona_id = a.id
                     ORDER BY pv.created_at DESC LIMIT 1
              ) v ON true
             ORDER BY a.id
            """
        ).fetchall()


def get_version(persona_id: str, version: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM persona_versions WHERE persona_id = %s AND version = %s",
            (persona_id, version),
        ).fetchone()


def get_asset(persona_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM persona_assets WHERE id = %s", (persona_id,)
        ).fetchone()


def get_version_by_id(version_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM persona_versions WHERE id = %s", (version_id,)
        ).fetchone()


# --- corpus docs / canon index ---------------------------------------------

def delete_canon_for_version(persona_version_id: str) -> None:
    """Drop corpus docs (and, by cascade, canon chunks) for a clean re-import."""
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM persona_corpus_docs WHERE persona_version_id = %s",
            (persona_version_id,),
        )


def insert_corpus_doc(persona_version_id: str, title: str, source_type: Optional[str],
                      text_uri: Optional[str], metadata: Optional[dict]) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO persona_corpus_docs
                (persona_version_id, title, source_type, text_uri, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (persona_version_id, title, source_type, text_uri,
             json.dumps(metadata) if metadata is not None else None),
        ).fetchone()


def insert_canon_chunk(persona_version_id: str, corpus_doc_id: str, chunk_index: int,
                       text: str, token_count: int, concepts: List[str],
                       vector: List[float]) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO persona_canon_chunks
                (persona_version_id, persona_corpus_doc_id, chunk_index, text,
                 token_count, concepts, embedding, embedding_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s)
            RETURNING id
            """,
            (persona_version_id, corpus_doc_id, chunk_index, text, token_count,
             json.dumps(concepts), _vec_literal(vector), None),
        ).fetchone()


def count_canon_chunks(persona_version_id: str) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT count(*) AS n FROM persona_canon_chunks WHERE persona_version_id = %s",
            (persona_version_id,),
        ).fetchone()["n"]


def search_canon(persona_version_id: str, query_vector: List[float], k: int = 6) -> List[dict]:
    """Cosine-nearest canon chunks for a persona version (design §10.4 persona_canon)."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT id, persona_corpus_doc_id, chunk_index, text, concepts,
                   1 - (embedding <=> %s::vector) AS score
              FROM persona_canon_chunks
             WHERE persona_version_id = %s AND embedding IS NOT NULL
             ORDER BY embedding <=> %s::vector
             LIMIT %s
            """,
            (_vec_literal(query_vector), persona_version_id,
             _vec_literal(query_vector), k),
        ).fetchall()
