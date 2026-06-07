"""LLM-judged QA dimensions (design §11.6).

Source grounding goes beyond M5's structural check (does the claim id resolve?)
to entailment: does the cited claim actually support what the speaker said?
Persona fidelity rates how in-character each speaker is.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..providers.llm import LLMProvider, LLMRequest, generate_structured
from .schemas import FIDELITY_SCHEMA, GROUNDING_SCHEMA

GROUNDING_PROMPT_VERSION = "script_qa_source_grounding_v0.1"
FIDELITY_PROMPT_VERSION = "script_qa_persona_fidelity_v0.1"

_GROUNDING_SYSTEM = (
    "You verify citations. For each segment that cites a source claim, decide "
    "whether the claim actually supports the line. Flag segments where the line "
    "asserts something the cited claim does not support, or makes an unsupported "
    "factual claim. Return an overall grounding score (0-1) and per-segment warnings."
)
_FIDELITY_SYSTEM = (
    "You rate how well each speaker stays in character given their persona stance "
    "and forbidden moves. Return a 0-1 score per speaker label, an overall "
    "distinctiveness score, and warnings for lines that break character."
)


def source_grounding(provider: LLMProvider, segments: List[Dict[str, Any]],
                     claims_by_id: Dict[str, str]) -> Dict[str, Any]:
    cited = [s for s in segments if any(e.get("type") == "source_material"
                                        for e in s.get("evidence", []))]
    if not cited:
        return {"score": 1.0, "warnings": []}
    lines = []
    for s in cited:
        cids = [e.get("claim_id") for e in s["evidence"] if e.get("type") == "source_material"]
        claim_text = "; ".join(claims_by_id.get(c, "(missing claim)") for c in cids)
        lines.append(f"[seg {s['segment_index']}] line: {s['text']}\n  cited claim: {claim_text}")
    req = LLMRequest(
        task_name="source_grounding_qa",
        prompt_version=GROUNDING_PROMPT_VERSION,
        system_prompt=_GROUNDING_SYSTEM,
        user_prompt="Verify each:\n\n" + "\n\n".join(lines),
        metadata={"segment_indices": [s["segment_index"] for s in cited]},
    )
    return generate_structured(provider, req, GROUNDING_SCHEMA)


def persona_fidelity(provider: LLMProvider, segments: List[Dict[str, Any]],
                     participants: List[Dict[str, Any]]) -> Dict[str, Any]:
    labels = [p["speaker_label"] for p in participants]
    persona_brief = "\n".join(
        f"{p['speaker_label']} ({p.get('persona_id')}): forbidden="
        f"{'; '.join(p.get('forbidden_moves') or [])}" for p in participants)
    transcript = "\n".join(f"[seg {s['segment_index']}] {s['speaker_label']}: {s['text']}"
                           for s in segments)
    req = LLMRequest(
        task_name="persona_fidelity_qa",
        prompt_version=FIDELITY_PROMPT_VERSION,
        system_prompt=_FIDELITY_SYSTEM,
        user_prompt=f"Personas:\n{persona_brief}\n\nTranscript:\n{transcript}",
        max_tokens=3000,
        metadata={"speaker_labels": labels},
    )
    return generate_structured(provider, req, FIDELITY_SCHEMA)
