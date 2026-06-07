"""qa_reports data access (design §8.15)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..db import get_conn


def insert_report(episode_id: str, script_version_id: str, report_type: str,
                  score_json: Dict[str, Any], warnings: List[dict]) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO qa_reports
                (episode_id, script_version_id, report_type, score_json, warnings)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (episode_id, script_version_id, report_type, json.dumps(score_json),
             json.dumps(warnings)),
        ).fetchone()


def list_reports(script_version_id: str) -> List[dict]:
    """Latest report per type for this script version."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT DISTINCT ON (report_type) *
              FROM qa_reports
             WHERE script_version_id = %s
             ORDER BY report_type, created_at DESC
            """,
            (script_version_id,),
        ).fetchall()
