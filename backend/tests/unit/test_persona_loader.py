from app.services.persona_loader import get_persona, load_personas


def test_loads_three_curated_personas():
    ids = {p["persona_id"] for p in load_personas()}
    assert {"laozi", "buddha", "modern_host"} <= ids


def test_get_persona_returns_asset_with_required_keys():
    buddha = get_persona("buddha", "v1.0")
    assert buddha is not None
    for key in ("identity_profile", "knowledge_boundary", "stance_matrix",
                "style_profile", "forbidden_moves", "voice_profile", "prompt_pack"):
        assert key in buddha, f"missing {key}"


def test_buddha_carries_safety_forbidden_moves():
    buddha = get_persona("buddha", "v1.0")
    joined = " ".join(buddha["forbidden_moves"]).lower()
    assert "medical" in joined or "psychiatric" in joined
    assert "authority" in joined


def test_unknown_persona_is_none():
    assert get_persona("aristotle", "v1.0") is None
    assert get_persona("laozi", "v9.9") is None
