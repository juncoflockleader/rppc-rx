"""Role context card + discussion plan generation (design §11.3, §11.4).

Both are schema-validated structured LLM calls. We pass real source-claim ids
and persona-canon concepts in `metadata` so the deterministic fake produces
output wired to real data (and the real providers get them in the prompt).
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..providers.llm import LLMProvider, LLMRequest, generate_structured
from .schemas import DISCUSSION_PLAN_SCHEMA, ROLE_CONTEXT_SCHEMA

ROLE_CONTEXT_PROMPT_VERSION = "role_context_card_v0.1"
DISCUSSION_PLAN_PROMPT_VERSION = "discussion_plan_v0.1"

_ROLE_SYSTEM = (
    "You prepare a role context card: how this persona will engage THIS episode's "
    "material. Stay within the persona's stance, style, and forbidden moves. "
    "Pick the source claims they would actually engage, name the persona concepts "
    "they bring, and the agreements/tensions with the other speakers."
)
_PLAN_SYSTEM = (
    "You design a philosophical dialogue as an ordered list of beats. Open with "
    "the host framing the question, give each guest distinct beats, create at "
    "least one point of tension, and end with a concrete takeaway. Allocate "
    "target_seconds so the beats sum near the episode duration and the host "
    "speaks ~40% with guests sharing the rest."
)


def _persona_brief(p: Dict[str, Any]) -> str:
    identity = (p.get("identity_profile") or {}).get("summary", "")
    stance = p.get("stance_matrix") or {}
    stance_lines = "; ".join(f"{k}: {v.get('position', v)}" for k, v in stance.items())
    forbidden = "; ".join(p.get("forbidden_moves") or [])
    return (f"{p['speaker_label']} ({p.get('persona_id')}): {identity}\n"
            f"Stances: {stance_lines}\nForbidden: {forbidden}")


def build_role_context(provider: LLMProvider, episode_goal: str, participant: Dict[str, Any],
                       source_claims: List[Dict[str, Any]],
                       canon_concepts: List[str], canon_snippets: List[str]) -> Dict[str, Any]:
    claim_ids = [str(c["id"]) for c in source_claims]
    claims_listing = "\n".join(f"- [{c['id']}] {c['claim_text']}" for c in source_claims)
    snippet_listing = "\n".join(f"- {s}" for s in canon_snippets[:5])
    prompt = (
        f"Episode goal: {episode_goal}\n\n"
        f"Persona:\n{_persona_brief(participant)}\n\n"
        f"Source claims (id, text):\n{claims_listing or '(none)'}\n\n"
        f"Relevant canon snippets:\n{snippet_listing or '(none)'}\n\n"
        "Produce the role context card."
    )
    req = LLMRequest(
        task_name="role_context",
        prompt_version=ROLE_CONTEXT_PROMPT_VERSION,
        system_prompt=_ROLE_SYSTEM,
        user_prompt=prompt,
        metadata={"persona_id": participant.get("persona_id"),
                  "claim_ids": claim_ids, "concepts": canon_concepts},
    )
    return generate_structured(provider, req, ROLE_CONTEXT_SCHEMA)


def build_discussion_plan(provider: LLMProvider, episode: Dict[str, Any],
                          participants: List[Dict[str, Any]],
                          source_claims: List[Dict[str, Any]],
                          cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    speaker_labels = [p["speaker_label"] for p in participants]
    # Host first so the fake/plan opens with the host.
    hosts = [p["speaker_label"] for p in participants if p.get("role") == "host"]
    ordered = hosts + [s for s in speaker_labels if s not in hosts]
    claim_ids = [str(c["id"]) for c in source_claims]
    concepts = sorted({c for card in cards
                       for c in (card.get("relevant_persona_concepts") or [])})
    goal = (episode.get("settings") or {}).get("goal") or episode.get("title") or ""

    prompt = (
        f"Episode goal: {goal}\n"
        f"Duration target (s): {episode['target_duration_seconds']}\n"
        f"Speakers (host first): {', '.join(ordered)}\n\n"
        f"Source claim ids: {', '.join(claim_ids) or '(none)'}\n"
        f"Persona concepts in play: {', '.join(concepts) or '(none)'}\n\n"
        "Design the beat structure."
    )
    req = LLMRequest(
        task_name="discussion_plan",
        prompt_version=DISCUSSION_PLAN_PROMPT_VERSION,
        system_prompt=_PLAN_SYSTEM,
        user_prompt=prompt,
        metadata={"speaker_labels": ordered,
                  "target_seconds": episode["target_duration_seconds"],
                  "claim_ids": claim_ids, "concepts": concepts,
                  "title": episode.get("title") or "Discussion plan"},
    )
    return generate_structured(provider, req, DISCUSSION_PLAN_SCHEMA)
