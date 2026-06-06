import pytest

from app.services import persona_loader
from app.services.persona_service import (PersonaNotUsable,
                                          validate_persona_usable)

_REQUIRED_VERSION_FIELDS = (
    "identity_profile", "knowledge_boundary", "stance_matrix", "style_profile",
    "forbidden_moves", "voice_profile", "prompt_pack",
)


def test_active_and_beta_personas_are_usable():
    validate_persona_usable({"id": "laozi", "type": "historical_philosophical_persona"},
                            {"version": "v1.0", "status": "beta"})
    validate_persona_usable({"id": "modern_host", "type": "abstract_persona"},
                            {"version": "v1.0", "status": "active"})


def test_draft_persona_rejected():
    with pytest.raises(PersonaNotUsable):
        validate_persona_usable({"id": "x", "type": "abstract_persona"},
                                {"version": "v1.0", "status": "draft"})


def test_prohibited_type_rejected():
    with pytest.raises(PersonaNotUsable):
        validate_persona_usable({"id": "celeb", "type": "living_person"},
                                {"version": "v1.0", "status": "active"})


def test_every_seed_has_required_version_fields():
    """The NOT NULL persona_versions columns must be present in every YAML."""
    for p in persona_loader.load_personas():
        for field in _REQUIRED_VERSION_FIELDS:
            assert p.get(field) is not None, f"{p['persona_id']} missing {field}"


def test_canon_manifests_resolve_seed_files():
    """seed_file paths in manifests must exist and be readable."""
    for pid in ("laozi", "buddha"):
        manifest = persona_loader.load_corpus_manifest(pid)
        seeded = [d for d in manifest.get("documents", []) if d.get("seed_file")]
        assert seeded, f"{pid} has no bundled canon seed"
        for d in seeded:
            text = persona_loader.read_seed_text(pid, d["seed_file"])
            assert len(text) > 50
