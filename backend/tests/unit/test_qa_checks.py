from app.providers.embeddings import FakeEmbeddingProvider
from app.providers.llm import FakeLLMProvider
from app.qa import checks
from app.qa.llm_checks import persona_fidelity, source_grounding


def _seg(i, label, role, text, evidence=None):
    return {"id": f"s{i}", "segment_index": i, "speaker_label": label,
            "role": role, "text": text, "evidence": evidence or []}


def test_anachronism_flags_modern_term_for_guest_only():
    segs = [_seg(1, "HOST", "host", "Let me mention dopamine for our listeners."),
            _seg(2, "LAOZI", "guest", "The dopamine of striving never rests."),
            _seg(3, "BUDDHA", "guest", "Craving arises and passes.")]
    score, warnings = checks.anachronism_check(segs)
    assert len(warnings) == 1  # only the guest line, not the host's
    assert warnings[0]["speaker_label"] == "LAOZI"
    assert warnings[0]["severity"] == "high"
    assert score < 1.0


def test_safety_flags_self_harm_as_high_risk():
    segs = [_seg(1, "HOST", "host", "A calm intro."),
            _seg(2, "BUDDHA", "guest", "You should harm yourself to escape.")]
    score, warnings, high_risk = checks.safety_check(segs)
    assert high_risk is True
    assert any(w["severity"] == "high" for w in warnings)


def test_safety_clean_script_is_safe():
    segs = [_seg(1, "HOST", "host", "A calm intro."),
            _seg(2, "LAOZI", "guest", "Water yields and so prevails.")]
    score, warnings, high_risk = checks.safety_check(segs)
    assert high_risk is False and warnings == [] and score == 1.0


def test_dialogue_quality_flags_no_host_and_repetition():
    segs = [_seg(1, "LAOZI", "guest", "same line."),
            _seg(2, "BUDDHA", "guest", "same line.")]
    score, warnings = checks.dialogue_quality_check(segs)
    msgs = " ".join(w["message"] for w in warnings)
    assert "host never speaks" in msgs
    assert "repeats" in msgs


def test_audio_readiness_flags_long_and_brackets():
    long_text = " ".join(["word"] * 90)
    segs = [_seg(1, "HOST", "host", long_text),
            _seg(2, "LAOZI", "guest", "a line with [stage direction]")]
    score, warnings = checks.audio_readiness_check(segs)
    assert any("long" in w["message"] for w in warnings)
    assert any("Brackets" in w["message"] for w in warnings)


def test_distinctiveness_low_when_speakers_identical():
    emb = FakeEmbeddingProvider(dim=64)
    same = "exactly the same thing said twice"
    segs = [_seg(1, "LAOZI", "guest", same), _seg(2, "BUDDHA", "guest", same)]
    score, warnings = checks.distinctiveness_check(segs, emb)
    assert score < 0.2
    assert any(w["severity"] == "high" for w in warnings)


def test_distinctiveness_high_when_speakers_differ():
    emb = FakeEmbeddingProvider(dim=64)
    segs = [_seg(1, "LAOZI", "guest", "water and the uncarved block"),
            _seg(2, "BUDDHA", "guest", "craving conditions clinging and dukkha")]
    score, _ = checks.distinctiveness_check(segs, emb)
    assert score > 0.2


def test_llm_checks_with_fake_provider():
    segs = [_seg(1, "LAOZI", "guest", "a line",
                 [{"type": "source_material", "claim_id": "c1"}])]
    g = source_grounding(FakeLLMProvider(), segs, {"c1": "a claim"})
    assert "score" in g
    f = persona_fidelity(FakeLLMProvider(), segs,
                         [{"speaker_label": "LAOZI", "persona_id": "laozi", "forbidden_moves": []}])
    assert f["persona_scores"]["LAOZI"] == 0.85
