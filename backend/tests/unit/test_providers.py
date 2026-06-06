import json

import pytest

from app.ingestion.analysis import CLAIMS_SCHEMA, SUMMARY_SCHEMA
from app.providers.embeddings import FakeEmbeddingProvider
from app.providers.llm import (FakeLLMProvider, LLMProvider, LLMRequest,
                               LLMResponse, SchemaValidationError,
                               generate_structured)


def _req(task):
    return LLMRequest(task_name=task, prompt_version="v0", system_prompt="s",
                      user_prompt="Modern desire is intensified by comparison.")


def test_fake_llm_summary_is_valid_and_deterministic():
    p = FakeLLMProvider()
    a = generate_structured(p, _req("source_summary"), SUMMARY_SCHEMA)
    b = generate_structured(p, _req("source_summary"), SUMMARY_SCHEMA)
    assert a == b
    assert "summary" in a and isinstance(a["themes"], list)


def test_fake_llm_claims_match_schema():
    p = FakeLLMProvider()
    out = generate_structured(p, _req("claim_extraction"), CLAIMS_SCHEMA)
    assert len(out["claims"]) >= 1
    assert "source_chunk_index" in out["claims"][0]


def test_fake_embeddings_deterministic_unit_norm():
    e = FakeEmbeddingProvider(dim=64)
    v1 = e.embed(["hello"])[0]
    v2 = e.embed(["hello"])[0]
    assert v1 == v2
    assert len(v1) == 64
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-6
    assert e.embed(["hello"])[0] != e.embed(["world"])[0]


class _SeqProvider(LLMProvider):
    """Returns preset texts in order — to exercise the repair/retry loop."""

    def __init__(self, texts):
        self._texts = list(texts)

    def generate_text(self, req):  # pragma: no cover
        return LLMResponse(text="")

    def generate_json(self, req, json_schema):
        return LLMResponse(text=self._texts.pop(0))


def test_structured_repairs_after_invalid_then_valid():
    valid = json.dumps({"summary": "ok", "themes": ["a"]})
    p = _SeqProvider(["not json at all", valid])
    out = generate_structured(p, _req("source_summary"), SUMMARY_SCHEMA, max_attempts=3)
    assert out["summary"] == "ok"


def test_structured_raises_after_exhausting_attempts():
    p = _SeqProvider(["nope", "still bad", "{not valid"])
    with pytest.raises(SchemaValidationError):
        generate_structured(p, _req("source_summary"), SUMMARY_SCHEMA, max_attempts=3)
