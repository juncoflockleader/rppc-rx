"""audio_segments / audio_mixes data access (design §8.16-8.17)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..db import get_conn


def mark_segment_audio_stale(script_segment_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE audio_segments SET status = 'stale' WHERE script_segment_id = %s AND status = 'rendered'",
            (script_segment_id,),
        )


def insert_segment_audio(script_segment_id: str, episode_id: str, speaker_label: str,
                         tts_provider: str, voice_id: str, audio_uri: str,
                         duration_ms: int, render_params: Dict[str, Any]) -> dict:
    with get_conn() as conn:
        conn.execute(
            "UPDATE audio_segments SET status = 'stale' WHERE script_segment_id = %s AND status = 'rendered'",
            (script_segment_id,),
        )
        return conn.execute(
            """
            INSERT INTO audio_segments
                (script_segment_id, episode_id, speaker_label, tts_provider, voice_id,
                 audio_uri, duration_ms, render_params, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'rendered')
            RETURNING *
            """,
            (script_segment_id, episode_id, speaker_label, tts_provider, voice_id,
             audio_uri, duration_ms, json.dumps(render_params)),
        ).fetchone()


def latest_segment_audio(script_segment_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM audio_segments
             WHERE script_segment_id = %s AND status = 'rendered'
             ORDER BY created_at DESC LIMIT 1
            """,
            (script_segment_id,),
        ).fetchone()


def ordered_latest_audio(script_version_id: str) -> List[dict]:
    """Latest rendered audio per segment for a script version, in segment order,
    joined to the segment's delivery (for pause insertion)."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT s.id AS segment_id, s.segment_index, s.delivery,
                   a.audio_uri, a.duration_ms
              FROM script_segments s
              JOIN LATERAL (
                   SELECT * FROM audio_segments aa
                    WHERE aa.script_segment_id = s.id AND aa.status = 'rendered'
                    ORDER BY aa.created_at DESC LIMIT 1
              ) a ON true
             WHERE s.script_version_id = %s
             ORDER BY s.segment_index
            """,
            (script_version_id,),
        ).fetchall()


def mark_episode_mixes_stale(episode_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE audio_mixes SET status = 'stale' WHERE episode_id = %s AND status = 'completed'",
            (episode_id,),
        )


def insert_mix(episode_id: str, script_version_id: str, audio_uri: str,
               duration_ms: int, format_: str, metadata: Dict[str, Any]) -> dict:
    with get_conn() as conn:
        conn.execute(
            "UPDATE audio_mixes SET status = 'stale' WHERE episode_id = %s AND status = 'completed'",
            (episode_id,),
        )
        return conn.execute(
            """
            INSERT INTO audio_mixes
                (episode_id, script_version_id, audio_uri, duration_ms, format, status, metadata)
            VALUES (%s, %s, %s, %s, %s, 'completed', %s)
            RETURNING *
            """,
            (episode_id, script_version_id, audio_uri, duration_ms, format_,
             json.dumps(metadata)),
        ).fetchone()


def get_latest_mix(episode_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT * FROM audio_mixes
             WHERE episode_id = %s
             ORDER BY (status = 'completed') DESC, created_at DESC LIMIT 1
            """,
            (episode_id,),
        ).fetchone()


def get_mix(mix_id: str) -> Optional[dict]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM audio_mixes WHERE id = %s", (mix_id,)).fetchone()
