"""Script version / segment / evidence-link data access (design §8.12-8.14)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..db import get_conn


def create_version(episode_id: str, source_discussion_plan_id: Optional[str]) -> dict:
    with get_conn() as conn:
        ver = conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS v FROM script_versions WHERE episode_id = %s",
            (episode_id,),
        ).fetchone()["v"]
        return conn.execute(
            """
            INSERT INTO script_versions
                (episode_id, version, source_discussion_plan_id, status)
            VALUES (%s, %s, %s, 'draft')
            RETURNING *
            """,
            (episode_id, ver, source_discussion_plan_id),
        ).fetchone()


def insert_segment(script_version_id: str, episode_id: str, segment_index: int,
                   beat_id: Optional[str], speaker_persona_version_id: Optional[str],
                   speaker_label: str, text: str, estimated_seconds: int) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO script_segments
                (script_version_id, episode_id, segment_index, beat_id,
                 speaker_persona_version_id, speaker_label, text, estimated_seconds)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (script_version_id, episode_id, segment_index, beat_id,
             speaker_persona_version_id, speaker_label, text, estimated_seconds),
        ).fetchone()


def insert_evidence(script_segment_id: str, evidence_type: str,
                    source_claim_id: Optional[str] = None,
                    source_chunk_id: Optional[str] = None,
                    persona_corpus_doc_id: Optional[str] = None,
                    concept: Optional[str] = None, notes: Optional[str] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO segment_evidence_links
                (script_segment_id, evidence_type, source_claim_id, source_chunk_id,
                 persona_corpus_doc_id, concept, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (script_segment_id, evidence_type, source_claim_id, source_chunk_id,
             persona_corpus_doc_id, concept, notes),
        )


def set_total(version_id: str, total_seconds: int, metadata: Dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE script_versions
               SET total_estimated_seconds = %s, metadata = %s, status = 'generated'
             WHERE id = %s
            """,
            (total_seconds, json.dumps(metadata), version_id),
        )


def get_latest(episode_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM script_versions WHERE episode_id = %s ORDER BY version DESC LIMIT 1",
            (episode_id,),
        ).fetchone()


def list_segments(version_id: str) -> List[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM script_segments WHERE script_version_id = %s ORDER BY segment_index",
            (version_id,),
        ).fetchall()


def list_evidence(segment_id: str) -> List[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM segment_evidence_links WHERE script_segment_id = %s",
            (segment_id,),
        ).fetchall()


def get_version_by_id(version_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM script_versions WHERE id = %s", (version_id,)
        ).fetchone()


def get_segment(segment_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM script_segments WHERE id = %s", (segment_id,)
        ).fetchone()


def list_needs_review(version_id: str) -> List[dict]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM script_segments
             WHERE script_version_id = %s AND status = 'needs_review'
             ORDER BY segment_index
            """,
            (version_id,),
        ).fetchall()


def update_segment_qa(segment_id: str, qa_json: Dict[str, Any], status: Optional[str]) -> None:
    with get_conn() as conn:
        if status is not None:
            conn.execute(
                "UPDATE script_segments SET qa_json = %s, status = %s, updated_at = now() WHERE id = %s",
                (json.dumps(qa_json), status, segment_id),
            )
        else:
            conn.execute(
                "UPDATE script_segments SET qa_json = %s, updated_at = now() WHERE id = %s",
                (json.dumps(qa_json), segment_id),
            )


def set_delivery(segment_id: str, delivery: Dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE script_segments SET delivery = %s, updated_at = now() WHERE id = %s",
            (json.dumps(delivery), segment_id),
        )


def set_version_qa(version_id: str, qa_summary: Dict[str, Any], safety_status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE script_versions SET qa_summary = %s, safety_status = %s WHERE id = %s",
            (json.dumps(qa_summary), safety_status, version_id),
        )


def update_segment_text(segment_id: str, text: str, estimated_seconds: int) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            UPDATE script_segments
               SET text = %s, estimated_seconds = %s, status = 'edited', updated_at = now()
             WHERE id = %s
            RETURNING *
            """,
            (text, estimated_seconds, segment_id),
        ).fetchone()
