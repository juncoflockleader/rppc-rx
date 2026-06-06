"""Source data access (raw SQL)."""
from __future__ import annotations

from typing import Optional

from ..db import get_conn


def create_source(project_id: str, type_: str, title: Optional[str],
                  original_filename: Optional[str], object_storage_uri: Optional[str],
                  status: str = "uploaded", metadata: Optional[dict] = None) -> dict:
    import json

    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO sources
                (project_id, type, title, original_filename, object_storage_uri,
                 status, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (project_id, type_, title, original_filename, object_storage_uri,
             status, json.dumps(metadata) if metadata is not None else None),
        ).fetchone()


def get_source(source_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM sources WHERE id = %s", (source_id,)).fetchone()


def list_sources(project_id: str) -> list[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM sources WHERE project_id = %s ORDER BY created_at",
            (project_id,),
        ).fetchall()


def set_summary(source_id: str, summary: str, themes: list) -> None:
    """Store the source-level summary + themes in metadata (design §11.1)."""
    import json

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE sources
               SET metadata = COALESCE(metadata, '{}'::jsonb)
                   || %s::jsonb,
                   updated_at = now()
             WHERE id = %s
            """,
            (json.dumps({"summary": summary, "themes": themes}), source_id),
        )


def set_object_storage_uri(source_id: str, uri: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE sources SET object_storage_uri = %s, updated_at = now() WHERE id = %s",
            (uri, source_id),
        )


def set_source_status(source_id: str, status: str,
                      parsed_text_uri: Optional[str] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE sources
               SET status = %s,
                   parsed_text_uri = COALESCE(%s, parsed_text_uri),
                   updated_at = now()
             WHERE id = %s
            """,
            (status, parsed_text_uri, source_id),
        )
