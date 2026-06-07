"""exports + usage + feedback data access (design §6.8, §20.3, §8.19)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..db import get_conn


# --- exports ---------------------------------------------------------------

def insert_export(episode_id: str, script_version_id: Optional[str], package_uri: str,
                  manifest: Dict[str, Any], format_: str = "zip") -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO exports (episode_id, script_version_id, package_uri, format, manifest)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (episode_id, script_version_id, package_uri, format_, json.dumps(manifest)),
        ).fetchone()


def get_latest_export(episode_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM exports WHERE episode_id = %s ORDER BY created_at DESC LIMIT 1",
            (episode_id,),
        ).fetchone()


def get_export(export_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM exports WHERE id = %s", (export_id,)).fetchone()


# --- usage rollup ----------------------------------------------------------

def usage_summary_for_episode(episode_id: str) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT
                COALESCE(SUM(input_tokens)  FILTER (WHERE kind='llm'), 0) AS llm_input_tokens,
                COALESCE(SUM(output_tokens) FILTER (WHERE kind='llm'), 0) AS llm_output_tokens,
                COALESCE(SUM(char_count)    FILTER (WHERE kind='tts'), 0) AS tts_chars,
                COALESCE(SUM(duration_ms)   FILTER (WHERE kind='tts'), 0) AS tts_duration_ms,
                COUNT(*) FILTER (WHERE kind='llm') AS llm_calls,
                COUNT(*) FILTER (WHERE kind='tts') AS tts_calls
              FROM usage_events
             WHERE episode_id = %s
            """,
            (episode_id,),
        ).fetchone()


def recent_usage(episode_id: Optional[str], limit: int = 100) -> List[dict]:
    with get_conn() as conn:
        if episode_id:
            return conn.execute(
                "SELECT * FROM usage_events WHERE episode_id = %s ORDER BY created_at DESC LIMIT %s",
                (episode_id, limit),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM usage_events ORDER BY created_at DESC LIMIT %s", (limit,)
        ).fetchall()


# --- feedback --------------------------------------------------------------

def insert_feedback(user_id: Optional[str], project_id: Optional[str],
                    episode_id: Optional[str], target_type: str, target_id: Optional[str],
                    feedback_type: str, rating: Optional[int], tags: Optional[list],
                    comment: Optional[str]) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO feedback_events
                (user_id, project_id, episode_id, target_type, target_id,
                 feedback_type, rating, tags, comment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (user_id, project_id, episode_id, target_type, target_id, feedback_type,
             rating, json.dumps(tags) if tags is not None else None, comment),
        ).fetchone()
