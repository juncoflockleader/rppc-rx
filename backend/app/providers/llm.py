"""LLM provider adapter (design §13).

Business code never calls a model SDK directly — it goes through `LLMProvider`.
This keeps the pipeline vendor-agnostic, makes prompt/task names + versions
explicit, and lets tests run on a deterministic fake with no network.

Structured output (§13.4): `generate_structured` returns a dict that has been
validated against a JSON schema, with a bounded repair/retry loop. Invalid JSON
never reaches the business layer.
"""
from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..config import get_settings

log = logging.getLogger("llm")


@dataclass
class LLMRequest:
    task_name: str
    prompt_version: str
    system_prompt: str
    user_prompt: str
    temperature: float = 0.0  # advisory; ignored by providers that don't accept it
    max_tokens: int = 4000
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str
    raw: Any = None
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(ABC):
    @abstractmethod
    def generate_text(self, req: LLMRequest) -> LLMResponse:
        ...

    @abstractmethod
    def generate_json(self, req: LLMRequest, json_schema: Dict[str, Any]) -> LLMResponse:
        """Return a response whose `.text` is a single JSON document matching schema."""


class SchemaValidationError(Exception):
    pass


def generate_structured(provider: LLMProvider, req: LLMRequest,
                        json_schema: Dict[str, Any], max_attempts: int = 3) -> Dict[str, Any]:
    """Generate + validate structured output with repair/retry (design §13.4).

    Attempt 1: generate. On invalid JSON or schema mismatch, attempt 2 asks the
    model to repair. Attempt 3 retries from scratch. After that, raise — the
    caller fails the job rather than letting invalid data into the database.
    """
    try:
        import jsonschema  # local import keeps it optional for non-LLM code paths
    except Exception:  # pragma: no cover
        jsonschema = None

    last_err = ""
    cur = req
    for attempt in range(1, max_attempts + 1):
        resp = provider.generate_json(cur, json_schema)
        try:
            data = json.loads(resp.text)
            if jsonschema is not None:
                jsonschema.validate(data, json_schema)
            return data
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            log.warning("structured output attempt %d failed (%s): %s",
                        attempt, req.task_name, last_err)
            cur = LLMRequest(
                task_name=req.task_name,
                prompt_version=req.prompt_version,
                system_prompt=req.system_prompt,
                user_prompt=(req.user_prompt + f"\n\nYour previous output was invalid "
                             f"({last_err}). Return ONLY valid JSON matching the schema."),
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                metadata=req.metadata,
            )
    raise SchemaValidationError(
        f"{req.task_name}: could not produce schema-valid JSON after "
        f"{max_attempts} attempts ({last_err})"
    )


# --- Fake (deterministic; default for dev/CI) -------------------------------

class FakeLLMProvider(LLMProvider):
    """Deterministic provider for tests and offline demos.

    Returns canned-but-plausible output keyed off the task name, derived
    deterministically from the input so the same source always yields the same
    claims/summary. No network.
    """

    def generate_text(self, req: LLMRequest) -> LLMResponse:
        return LLMResponse(text=f"[fake:{req.task_name}] {req.user_prompt[:120]}",
                           input_tokens=len(req.user_prompt) // 4, output_tokens=20)

    def generate_json(self, req: LLMRequest, json_schema: Dict[str, Any]) -> LLMResponse:
        data = self._canned(req)
        return LLMResponse(text=json.dumps(data),
                           input_tokens=len(req.user_prompt) // 4, output_tokens=40)

    def _canned(self, req: LLMRequest) -> Dict[str, Any]:
        seed = hashlib.sha256(req.user_prompt.encode()).hexdigest()
        if req.task_name.startswith("source_summary"):
            return {
                "summary": f"Deterministic summary of the source ({seed[:8]}).",
                "themes": ["desire", "comparison", "anxiety"],
            }
        if req.task_name.startswith("claim_extraction"):
            # Two stable claims so downstream evidence-linking has something real.
            return {
                "claims": [
                    {"claim_text": "The source argues a central point.",
                     "claim_type": "argument", "source_chunk_index": 0,
                     "page_number": 1, "confidence": 0.8},
                    {"claim_text": "The source supports it with an example.",
                     "claim_type": "example", "source_chunk_index": 0,
                     "page_number": 1, "confidence": 0.6},
                ],
                "themes": ["desire", "comparison"],
            }
        if req.task_name.startswith("role_context"):
            return {
                "persona_id": req.metadata.get("persona_id", "persona"),
                "episode_position": "A grounded position drawn from this persona's stance.",
                "relevant_source_claim_ids": req.metadata.get("claim_ids", []),
                "relevant_persona_concepts": req.metadata.get("concepts", []),
                "likely_agreements": ["Shares the framing that the topic matters."],
                "likely_tensions": ["Would resist over-analysis and modern jargon."],
                "style_reminders": ["Keep responses in character.",
                                    "Let the host introduce modern terms."],
                "forbidden_moves": ["Do not claim to be the real historical figure."],
            }
        if req.task_name.startswith("discussion_plan"):
            speakers = req.metadata.get("speaker_labels", ["HOST"])
            host = speakers[0]
            guests = speakers[1:] or [host]
            target = req.metadata.get("target_seconds", 600)
            beats = [
                {"beat_id": "opening", "title": "Framing the question",
                 "goal": "Introduce the material and frame the question.",
                 "primary_speaker": host, "target_seconds": int(target * 0.15),
                 "source_claim_ids": req.metadata.get("claim_ids", [])[:1],
                 "persona_concepts": []},
            ]
            for i, g in enumerate(guests, start=1):
                beats.append({
                    "beat_id": f"beat_{i}",
                    "title": f"{g} responds",
                    "goal": f"Let {g} bring their distinct perspective.",
                    "primary_speaker": g,
                    "target_seconds": int(target * (0.7 / max(1, len(guests)))),
                    "source_claim_ids": req.metadata.get("claim_ids", []),
                    "persona_concepts": req.metadata.get("concepts", []),
                })
            beats.append({
                "beat_id": "closing", "title": "Modern application",
                "goal": "Host ties it to a concrete modern example.",
                "primary_speaker": host, "target_seconds": int(target * 0.15),
                "source_claim_ids": [], "persona_concepts": []})
            return {
                "title": req.metadata.get("title", "Generated discussion plan"),
                "beats": beats,
                "ending": {"takeaway": "Less forcing, clearer seeing."},
            }
        if req.task_name.startswith("script_generation"):
            return self._canned_script(req)
        if req.task_name.startswith("segment_rewrite"):
            return {"text": "[rewritten] " + req.metadata.get("instruction", "tightened.")}
        if req.task_name.startswith("source_grounding_qa"):
            return {"score": 0.9, "warnings": []}
        if req.task_name.startswith("persona_fidelity_qa"):
            labels = req.metadata.get("speaker_labels", [])
            return {"persona_scores": {label: 0.85 for label in labels},
                    "distinctiveness_score": 0.8, "warnings": []}
        return {}

    def _canned_script(self, req: LLMRequest) -> Dict[str, Any]:
        beats = req.metadata.get("beats", [])
        host = req.metadata.get("host_label", "HOST")
        claim_ids = req.metadata.get("claim_ids", [])
        concepts = req.metadata.get("concepts", []) or ["the point"]
        segs: List[Dict[str, Any]] = []
        idx = 1
        for b_i, b in enumerate(beats):
            beat_id = b.get("beat_id", f"beat_{b_i}")
            speaker = b.get("primary_speaker", host)
            if speaker == host:
                evidence = [{"type": "host_bridge"}]
                if claim_ids:
                    evidence.append({"type": "source_material", "claim_id": claim_ids[0]})
                text = ("Here's the question from the material, in plain terms, "
                        "and what each of you makes of it.")
            else:
                evidence = [{"type": "persona_canon", "concept": concepts[b_i % len(concepts)]},
                            {"type": "creative_bridge"}]
                text = ("Speaking from where I stand, the matter looks different "
                        "than the forcing the modern world prefers.")
            segs.append({"segment_index": idx, "beat_id": beat_id,
                         "speaker_label": speaker, "text": text,
                         "estimated_seconds": 12, "evidence": evidence})
            idx += 1
            # Host steps in after each guest beat (design §11.5 cadence).
            if speaker != host:
                segs.append({
                    "segment_index": idx, "beat_id": beat_id, "speaker_label": host,
                    "text": "So, to put that in modern terms for our listeners...",
                    "estimated_seconds": 8,
                    "evidence": [{"type": "host_bridge"}]
                    + ([{"type": "source_material", "claim_id": claim_ids[0]}] if claim_ids else []),
                })
                idx += 1
        return {"segments": segs}


# --- Anthropic --------------------------------------------------------------

class AnthropicLLMProvider(LLMProvider):
    """Claude via the official Anthropic SDK (design default model: claude-opus-4-8).

    Structured output uses output_config.format (json_schema). Adaptive thinking
    is on. The SDK is imported lazily so this module loads without `anthropic`.
    """

    def __init__(self) -> None:
        import anthropic  # lazy

        s = get_settings()
        key = s.anthropic_api_key or s.llm_api_key or None
        self._client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
        self._model = s.llm_model

    def generate_text(self, req: LLMRequest) -> LLMResponse:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=req.max_tokens,
            thinking={"type": "adaptive"},
            system=req.system_prompt,
            messages=[{"role": "user", "content": req.user_prompt}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
        return LLMResponse(text=text, raw=msg,
                           input_tokens=msg.usage.input_tokens,
                           output_tokens=msg.usage.output_tokens)

    def generate_json(self, req: LLMRequest, json_schema: Dict[str, Any]) -> LLMResponse:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=req.max_tokens,
            system=req.system_prompt,
            messages=[{"role": "user", "content": req.user_prompt}],
            output_config={"format": {"type": "json_schema", "schema": json_schema}},
        )
        text = next((b.text for b in msg.content if b.type == "text"), "")
        return LLMResponse(text=text, raw=msg,
                           input_tokens=msg.usage.input_tokens,
                           output_tokens=msg.usage.output_tokens)


# --- OpenAI -----------------------------------------------------------------

class OpenAILLMProvider(LLMProvider):
    """OpenAI chat-completions adapter. Tests use the fake; this is faked in CI."""

    def __init__(self) -> None:
        from openai import OpenAI  # lazy

        s = get_settings()
        self._client = OpenAI(api_key=s.openai_api_key or None)
        self._model = s.openai_llm_model

    def generate_text(self, req: LLMRequest) -> LLMResponse:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": req.system_prompt},
                      {"role": "user", "content": req.user_prompt}],
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        return LLMResponse(text=resp.choices[0].message.content or "", raw=resp,
                           input_tokens=resp.usage.prompt_tokens,
                           output_tokens=resp.usage.completion_tokens)

    def generate_json(self, req: LLMRequest, json_schema: Dict[str, Any]) -> LLMResponse:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": req.system_prompt},
                      {"role": "user", "content": req.user_prompt}],
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": req.task_name, "schema": json_schema},
            },
        )
        return LLMResponse(text=resp.choices[0].message.content or "", raw=resp,
                           input_tokens=resp.usage.prompt_tokens,
                           output_tokens=resp.usage.completion_tokens)


_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        name = get_settings().llm_provider
        if name == "anthropic":
            _provider = AnthropicLLMProvider()
        elif name == "openai":
            _provider = OpenAILLMProvider()
        else:
            _provider = FakeLLMProvider()
    return _provider


def reset_llm_provider() -> None:
    """Test hook — drop the cached provider so a new config takes effect."""
    global _provider
    _provider = None
