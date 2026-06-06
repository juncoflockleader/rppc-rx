"""source_chunks data access (raw SQL), including pgvector embedding writes."""
from __future__ import annotations

from typing import List, Optional

from ..db import get_conn


def _vec_literal(vec: List[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def insert_chunks(source_id: str, project_id: str, chunks: List[dict]) -> List[dict]:
    """chunks: list of {chunk_index, text, token_count, page_start, page_end,
    char_start, char_end}. Returns inserted rows (with ids)."""
    out = []
    with get_conn() as conn:
        for c in chunks:
            row = conn.execute(
                """
                INSERT INTO source_chunks
                    (source_id, project_id, chunk_index, text, token_count,
                     page_start, page_end, char_start, char_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (source_id, project_id, c["chunk_index"], c["text"],
                 c.get("token_count"), c.get("page_start"), c.get("page_end"),
                 c.get("char_start"), c.get("char_end")),
            ).fetchone()
            out.append(row)
    return out


def set_embedding(chunk_id: str, vector: List[float]) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE source_chunks SET embedding = %s::vector, embedding_id = %s WHERE id = %s",
            (_vec_literal(vector), str(chunk_id), chunk_id),
        )


def list_chunks(source_id: str) -> List[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM source_chunks WHERE source_id = %s ORDER BY chunk_index",
            (source_id,),
        ).fetchall()


def count_chunks(source_id: str) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT count(*) AS n FROM source_chunks WHERE source_id = %s", (source_id,)
        ).fetchone()["n"]


def search_project(project_id: str, query_vector: List[float], k: int = 6) -> List[dict]:
    """Cosine-nearest chunks within a project (design §10.4 project_source)."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT id, source_id, chunk_index, text, page_start, page_end,
                   1 - (embedding <=> %s::vector) AS score
              FROM source_chunks
             WHERE project_id = %s AND embedding IS NOT NULL
             ORDER BY embedding <=> %s::vector
             LIMIT %s
            """,
            (_vec_literal(query_vector), project_id, _vec_literal(query_vector), k),
        ).fetchall()
