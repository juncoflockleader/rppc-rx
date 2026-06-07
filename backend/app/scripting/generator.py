"""Script generation + single-segment rewrite (design §11.5, §9).

Structured LLM calls. The deterministic fake is driven via `metadata` (beats,
host label, real claim ids, persona concepts) so generated evidence links point
at real rows.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..providers.llm import LLMProvider, LLMRequest, generate_structured
from .schemas import REWRITE_SCHEMA, SCRIPT_SCHEMA

SCRIPT_PROMPT_VERSION = "script_generation_v0.1"
REWRITE_PROMPT_VERSION = "segment_rewrite_v0.1"

_SCRIPT_SYSTEM = (
    "You write a multi-speaker podcast script from a discussion plan. Rules: one "
    "speaker per segment; each segment belongs to a beat; keep each persona's "
    "voice distinct; the host owns modern terminology and explains/clarifies "
    "every few guest segments; guests avoid modern jargon; no instant consensus; "
    "never say you are an AI or the real historical figure. For each segment give "
    "evidence: source_material (with claim_id), persona_canon (with concept), "
    "host_bridge, creative_bridge, or unsupported_or_needs_review for anything "
    "uncertain. Keep segments short (host 15-40 words, guests 10-40)."
)
_REWRITE_SYSTEM = (
    "You rewrite a single podcast line per the instruction while keeping the "
    "speaker's persona, stance, and forbidden moves. Return only the new line."
)


def build_script(provider: LLMProvider, episode: Dict[str, Any], plan: Dict[str, Any],
                 cards: List[Dict[str, Any]], source_claims: List[Dict[str, Any]],
                 host_label: str) -> Dict[str, Any]:
    beats = plan.get("beats", [])
    claim_ids = [str(c["id"]) for c in source_claims]
    concepts = sorted({c for card in cards
                       for c in (card.get("relevant_persona_concepts") or [])})
    beats_brief = "\n".join(
        f"- {b['beat_id']} [{b.get('primary_speaker', host_label)}]: {b['goal']} "
        f"(~{b.get('target_seconds', 0)}s)" for b in beats)
    cards_brief = "\n".join(
        f"- {c.get('speaker_label', c.get('persona_id'))}: {c.get('episode_position','')}"
        for c in cards)
    prompt = (
        f"Episode: {episode.get('title')} (target {episode['target_duration_seconds']}s)\n"
        f"Host speaker label: {host_label}\n\n"
        f"Beats:\n{beats_brief}\n\n"
        f"Role context:\n{cards_brief}\n\n"
        f"Source claim ids: {', '.join(claim_ids) or '(none)'}\n"
        f"Persona concepts: {', '.join(concepts) or '(none)'}\n\n"
        "Write the full script as segments."
    )
    req = LLMRequest(
        task_name="script_generation",
        prompt_version=SCRIPT_PROMPT_VERSION,
        system_prompt=_SCRIPT_SYSTEM,
        user_prompt=prompt,
        max_tokens=6000,
        metadata={"beats": [{"beat_id": b["beat_id"],
                             "primary_speaker": b.get("primary_speaker", host_label)}
                            for b in beats],
                  "host_label": host_label, "claim_ids": claim_ids,
                  "concepts": concepts},
    )
    return generate_structured(provider, req, SCRIPT_SCHEMA)


def rewrite_segment(provider: LLMProvider, segment: Dict[str, Any],
                    instruction: str, persona_brief: str) -> str:
    prompt = (
        f"Speaker {segment['speaker_label']}. Persona notes:\n{persona_brief}\n\n"
        f"Current line:\n{segment['text']}\n\n"
        f"Instruction: {instruction}\n\nReturn the rewritten line."
    )
    req = LLMRequest(
        task_name="segment_rewrite",
        prompt_version=REWRITE_PROMPT_VERSION,
        system_prompt=_REWRITE_SYSTEM,
        user_prompt=prompt,
        metadata={"instruction": instruction},
    )
    out = generate_structured(provider, req, REWRITE_SCHEMA)
    return out["text"]
