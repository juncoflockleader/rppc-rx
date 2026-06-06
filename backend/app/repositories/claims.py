"""source_claims data access (raw SQL)."""
from __future__ import annotations

import json
from typing import List, Optional

from ..db import get_conn


def insert_claims(source_id: str, project_id: str, claims: List[dict],
                  chunk_id_by_index: Optional[dict] = None) -> List[dict]:
    """claims: list of {claim_text, claim_type, confidence, source_chunk_index,
    page_number}. chunk_id_by_index maps a chunk_index -> chunk uuid for linking."""
    chunk_id_by_index = chunk_id_by_index or {}
    out = []
    with get_conn() as conn:
        for c in claims:
            chunk_id = chunk_id_by_index.get(c.get("source_chunk_index"))
            row = conn.execute(
                """
                INSERT INTO source_claims
                    (source_id, project_id, claim_text, claim_type, confidence,
                     source_chunk_id, page_number, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (source_id, project_id, c["claim_text"], c.get("claim_type"),
                 c.get("confidence"), chunk_id, c.get("page_number"),
                 json.dumps({"raw_chunk_index": c.get("source_chunk_index")})),
            ).fetchone()
            out.append(row)
    return out


def list_claims(source_id: str) -> List[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM source_claims WHERE source_id = %s ORDER BY created_at",
            (source_id,),
        ).fetchall()
