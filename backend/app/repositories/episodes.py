"""Episode / participant / discussion-plan / role-context data access."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..db import get_conn


# --- episodes ---------------------------------------------------------------

def create_episode(project_id: str, title: Optional[str], target_language: str,
                   target_duration_seconds: int, format_: str, audience: Optional[str],
                   style: Optional[str], settings: Optional[dict]) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO episodes
                (project_id, title, target_language, target_duration_seconds,
                 format, audience, style, settings)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (project_id, title, target_language, target_duration_seconds, format_,
             audience, style, json.dumps(settings) if settings is not None else None),
        ).fetchone()


def get_episode(episode_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM episodes WHERE id = %s", (episode_id,)
        ).fetchone()


def set_episode_status(episode_id: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE episodes SET status = %s, updated_at = now() WHERE id = %s",
            (status, episode_id),
        )


# --- participants -----------------------------------------------------------

def add_persona(episode_id: str, persona_version_id: str, role: str,
                speaker_label: str, sort_order: int) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO episode_personas
                (episode_id, persona_version_id, role, speaker_label, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (episode_id, persona_version_id, role, speaker_label, sort_order),
        ).fetchone()


def list_personas(episode_id: str) -> List[dict]:
    """Participants joined to their persona asset (for prompts/labels)."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT ep.*, pv.persona_id, pv.version, pv.identity_profile,
                   pv.stance_matrix, pv.style_profile, pv.forbidden_moves,
                   pv.knowledge_boundary, pv.voice_profile
              FROM episode_personas ep
              JOIN persona_versions pv ON pv.id = ep.persona_version_id
             WHERE ep.episode_id = %s
             ORDER BY ep.sort_order
            """,
            (episode_id,),
        ).fetchall()


# --- discussion plans -------------------------------------------------------

def create_plan(episode_id: str, plan_json: Dict[str, Any]) -> dict:
    with get_conn() as conn:
        ver = conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS v FROM discussion_plans WHERE episode_id = %s",
            (episode_id,),
        ).fetchone()["v"]
        return conn.execute(
            """
            INSERT INTO discussion_plans (episode_id, version, plan_json, status)
            VALUES (%s, %s, %s, 'draft')
            RETURNING *
            """,
            (episode_id, ver, json.dumps(plan_json)),
        ).fetchone()


def get_latest_plan(episode_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM discussion_plans WHERE episode_id = %s ORDER BY version DESC LIMIT 1",
            (episode_id,),
        ).fetchone()


# --- role context cards -----------------------------------------------------

def next_card_version(episode_id: str) -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS v FROM role_context_cards WHERE episode_id = %s",
            (episode_id,),
        ).fetchone()["v"]


def insert_card(episode_id: str, persona_version_id: str, speaker_label: str,
                version: int, card_json: Dict[str, Any]) -> dict:
    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO role_context_cards
                (episode_id, persona_version_id, speaker_label, version, card_json)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (episode_id, persona_version_id, speaker_label, version,
             json.dumps(card_json)),
        ).fetchone()


def latest_cards(episode_id: str) -> List[dict]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT DISTINCT ON (speaker_label) *
              FROM role_context_cards
             WHERE episode_id = %s
             ORDER BY speaker_label, version DESC
            """,
            (episode_id,),
        ).fetchall()
