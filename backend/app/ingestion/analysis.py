"""Source understanding via the LLM provider (design §11.1 steps 6-7).

Summary + theme extraction and claim extraction, both as schema-validated
structured output. Prompts are versioned (§13.2).
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..providers.llm import LLMProvider, LLMRequest, generate_structured

SUMMARY_PROMPT_VERSION = "source_summary_v0.1"
CLAIMS_PROMPT_VERSION = "claim_extraction_v0.1"

SUMMARY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["summary", "themes"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "themes": {"type": "array", "items": {"type": "string"}},
    },
}

CLAIMS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["claims", "themes"],
    "additionalProperties": False,
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["claim_text", "claim_type", "source_chunk_index"],
                "additionalProperties": False,
                "properties": {
                    "claim_text": {"type": "string"},
                    "claim_type": {"type": "string"},
                    "source_chunk_index": {"type": "integer"},
                    "page_number": {"type": "integer"},
                    "confidence": {"type": "number"},
                },
            },
        },
        "themes": {"type": "array", "items": {"type": "string"}},
    },
}

_SUMMARY_SYSTEM = (
    "You summarize source material for a podcast discussion. Be faithful to the "
    "text; do not add facts. Return a concise summary and 3-6 key themes."
)
_CLAIMS_SYSTEM = (
    "You extract the key claims a source makes, so personas can later discuss "
    "them. Each claim must be grounded in the text. claim_type is one of: "
    "argument, definition, example, evidence, quote, question, counterargument. "
    "source_chunk_index is the 0-based index of the chunk the claim comes from."
)


def summarize(provider: LLMProvider, full_text: str) -> Dict[str, Any]:
    req = LLMRequest(
        task_name="source_summary",
        prompt_version=SUMMARY_PROMPT_VERSION,
        system_prompt=_SUMMARY_SYSTEM,
        user_prompt=f"Source material:\n\n{full_text[:12000]}",
    )
    return generate_structured(provider, req, SUMMARY_SCHEMA)


def extract_claims(provider: LLMProvider, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Give the model indexed chunks so claim.source_chunk_index is meaningful.
    listing = "\n\n".join(
        f"[chunk {c['chunk_index']} | page {c.get('page_start', 1)}]\n{c['text'][:1500]}"
        for c in chunks[:30]
    )
    req = LLMRequest(
        task_name="claim_extraction",
        prompt_version=CLAIMS_PROMPT_VERSION,
        system_prompt=_CLAIMS_SYSTEM,
        user_prompt=f"Chunks:\n\n{listing}",
        max_tokens=3000,
    )
    return generate_structured(provider, req, CLAIMS_SCHEMA)
