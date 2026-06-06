"""Project + user data access (raw SQL)."""
from __future__ import annotations

from typing import Any, Optional

from ..db import get_conn


def ensure_dev_user(email: str = "dev@example.com", display_name: str = "Dev User") -> dict:
    """Idempotently return a user row. Stand-in for real auth in M1."""
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO users (email, display_name)
            VALUES (%s, %s)
            ON CONFLICT (email) DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING *
            """,
            (email, display_name),
        ).fetchone()
        return row


def create_project(user_id: str, title: str, description: Optional[str],
                   default_language: str = "en") -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO projects (user_id, title, description, default_language)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (user_id, title, description, default_language),
        ).fetchone()


def get_project(project_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM projects WHERE id = %s", (project_id,)
        ).fetchone()


def list_projects(user_id: str) -> list[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM projects WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()


def set_project_status(project_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE projects SET status = %s, updated_at = now() WHERE id = %s",
            (status, project_id),
        )


def delete_project(project_id: str) -> None:
    """FK cascades remove sources/episodes/scripts/audio (design §19.4)."""
    with get_conn() as conn:
        conn.execute("DELETE FROM projects WHERE id = %s", (project_id,))
