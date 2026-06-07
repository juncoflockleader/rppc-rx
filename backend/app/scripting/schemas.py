"""JSON schemas for script generation + rewrite (design §14.2, §11.5)."""
from __future__ import annotations

from typing import Any, Dict

EVIDENCE_TYPES = [
    "source_material", "persona_canon", "host_bridge", "creative_bridge",
    "unsupported_or_needs_review",
]

SCRIPT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["segments"],
    "additionalProperties": False,
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["segment_index", "beat_id", "speaker_label", "text",
                             "estimated_seconds", "evidence"],
                "additionalProperties": False,
                "properties": {
                    "segment_index": {"type": "integer"},
                    "beat_id": {"type": "string"},
                    "speaker_label": {"type": "string"},
                    "text": {"type": "string"},
                    "estimated_seconds": {"type": "integer"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type"],
                            "additionalProperties": False,
                            "properties": {
                                "type": {"type": "string", "enum": EVIDENCE_TYPES},
                                "claim_id": {"type": "string"},
                                "concept": {"type": "string"},
                                "notes": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}

REWRITE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["text"],
    "additionalProperties": False,
    "properties": {"text": {"type": "string"}},
}
