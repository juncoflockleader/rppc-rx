"""JSON schemas for episode-planning structured output (design §11.3, §11.4, §14.1)."""
from __future__ import annotations

from typing import Any, Dict

ROLE_CONTEXT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["persona_id", "episode_position"],
    "additionalProperties": False,
    "properties": {
        "persona_id": {"type": "string"},
        "episode_position": {"type": "string"},
        "relevant_source_claim_ids": {"type": "array", "items": {"type": "string"}},
        "relevant_persona_concepts": {"type": "array", "items": {"type": "string"}},
        "likely_agreements": {"type": "array", "items": {"type": "string"}},
        "likely_tensions": {"type": "array", "items": {"type": "string"}},
        "style_reminders": {"type": "array", "items": {"type": "string"}},
        "forbidden_moves": {"type": "array", "items": {"type": "string"}},
    },
}

DISCUSSION_PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["title", "beats"],
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "beats": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["beat_id", "title", "goal", "target_seconds"],
                "additionalProperties": False,
                "properties": {
                    "beat_id": {"type": "string"},
                    "title": {"type": "string"},
                    "goal": {"type": "string"},
                    "primary_speaker": {"type": "string"},
                    "target_seconds": {"type": "integer"},
                    "source_claim_ids": {"type": "array", "items": {"type": "string"}},
                    "persona_concepts": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "ending": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"takeaway": {"type": "string"}},
        },
    },
}
