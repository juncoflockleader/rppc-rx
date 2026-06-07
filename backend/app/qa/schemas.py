"""Schemas for LLM QA dimensions (design §14.3)."""
from __future__ import annotations

from typing import Any, Dict

GROUNDING_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["score", "warnings"],
    "additionalProperties": False,
    "properties": {
        "score": {"type": "number"},
        "warnings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["segment_index", "severity", "message"],
                "additionalProperties": False,
                "properties": {
                    "segment_index": {"type": "integer"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "message": {"type": "string"},
                    "suggested_action": {"type": "string"},
                },
            },
        },
    },
}

FIDELITY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["persona_scores"],
    "additionalProperties": False,
    "properties": {
        "persona_scores": {"type": "object", "additionalProperties": {"type": "number"}},
        "distinctiveness_score": {"type": "number"},
        "warnings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["segment_index", "severity", "message"],
                "additionalProperties": False,
                "properties": {
                    "segment_index": {"type": "integer"},
                    "speaker_label": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "message": {"type": "string"},
                    "suggested_rewrite": {"type": "string"},
                },
            },
        },
    },
}
