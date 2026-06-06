from app.planning.generator import build_discussion_plan, build_role_context
from app.planning.schemas import DISCUSSION_PLAN_SCHEMA, ROLE_CONTEXT_SCHEMA
from app.providers.llm import FakeLLMProvider

import jsonschema

PARTICIPANT = {
    "speaker_label": "LAOZI", "persona_id": "laozi", "role": "guest",
    "persona_version_id": "00000000-0000-0000-0000-000000000001",
    "identity_profile": {"summary": "Daoist persona."},
    "stance_matrix": {"desire": {"position": "forced striving distorts"}},
    "forbidden_moves": ["Do not mention dopamine."],
}
CLAIMS = [{"id": "c1", "claim_text": "Desire is amplified by comparison."},
          {"id": "c2", "claim_text": "Comparison fuels craving."}]


def test_role_context_card_valid_and_wired_to_data():
    card = build_role_context(FakeLLMProvider(), "Understand desire", PARTICIPANT,
                              CLAIMS, ["wu wei", "simplicity"], ["snippet about water"])
    jsonschema.validate(card, ROLE_CONTEXT_SCHEMA)
    assert card["relevant_source_claim_ids"] == ["c1", "c2"]
    assert "wu wei" in card["relevant_persona_concepts"]
    assert card["forbidden_moves"]


def test_discussion_plan_valid_with_host_opening():
    episode = {"target_duration_seconds": 600, "title": "Desire",
               "settings": {"goal": "Understand desire"}}
    participants = [
        {"speaker_label": "HOST", "role": "host"},
        {"speaker_label": "LAOZI", "role": "guest"},
        {"speaker_label": "BUDDHA", "role": "guest"},
    ]
    cards = [{"relevant_persona_concepts": ["wu wei"]},
             {"relevant_persona_concepts": ["craving"]}]
    plan = build_discussion_plan(FakeLLMProvider(), episode, participants, CLAIMS, cards)
    jsonschema.validate(plan, DISCUSSION_PLAN_SCHEMA)

    beats = plan["beats"]
    assert len(beats) >= 3
    assert beats[0]["primary_speaker"] == "HOST"
    total = sum(b["target_seconds"] for b in beats)
    assert 0 < total <= episode["target_duration_seconds"]
    # both guests get a beat
    speakers = {b["primary_speaker"] for b in beats}
    assert {"HOST", "LAOZI", "BUDDHA"} <= speakers
