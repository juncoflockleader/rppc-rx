import jsonschema

from app.providers.llm import FakeLLMProvider
from app.scripting.estimate import estimate_seconds
from app.scripting.generator import build_script, rewrite_segment
from app.scripting.schemas import SCRIPT_SCHEMA

EPISODE = {"title": "Desire", "target_duration_seconds": 600}
PLAN = {"beats": [
    {"beat_id": "opening", "primary_speaker": "HOST", "goal": "frame", "target_seconds": 60},
    {"beat_id": "beat_1", "primary_speaker": "LAOZI", "goal": "reframe", "target_seconds": 200},
    {"beat_id": "beat_2", "primary_speaker": "BUDDHA", "goal": "diagnose", "target_seconds": 200},
]}
CARDS = [{"speaker_label": "LAOZI", "relevant_persona_concepts": ["wu wei"]},
         {"speaker_label": "BUDDHA", "relevant_persona_concepts": ["craving"]}]
CLAIMS = [{"id": "c1", "claim_text": "Desire is amplified by comparison."}]


def test_estimate_seconds_by_role():
    text = " ".join(["word"] * 50)
    assert estimate_seconds(text, "host") == round(50 / 2.5)
    assert estimate_seconds(text, "guest") == round(50 / 2.0)
    assert estimate_seconds("", "guest") == 1


def test_build_script_valid_with_distinct_speakers_and_evidence():
    script = build_script(FakeLLMProvider(), EPISODE, PLAN, CARDS, CLAIMS, "HOST")
    jsonschema.validate(script, SCRIPT_SCHEMA)
    segs = script["segments"]
    assert len(segs) >= 4
    speakers = {s["speaker_label"] for s in segs}
    assert {"HOST", "LAOZI", "BUDDHA"} <= speakers
    # every segment carries at least one evidence entry
    assert all(s["evidence"] for s in segs)
    types = {e["type"] for s in segs for e in s["evidence"]}
    assert "host_bridge" in types and "persona_canon" in types
    # source_material evidence references the real claim id
    src = [e for s in segs for e in s["evidence"] if e["type"] == "source_material"]
    assert src and src[0]["claim_id"] == "c1"


def test_rewrite_returns_new_text():
    out = rewrite_segment(FakeLLMProvider(),
                          {"speaker_label": "LAOZI", "text": "old line"},
                          "make it more concise", "tone: calm; forbidden: no jargon")
    assert "make it more concise" in out
