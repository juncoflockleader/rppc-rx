"""Rule-based QA checks (design §11.6) + the engineered distinctiveness proxy.

These are deterministic — no LLM — so they're cheap, reproducible, and (for
distinctiveness) measure a real property instead of asking a model to grade
itself. Each returns (score: float, warnings: list[dict]).
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

# Modern vocabulary an ancient guest should not use in their own voice (§11.6
# anachronism). The host may use these.
MODERN_TERMS = [
    "dopamine", "algorithm", "algorithmic", "internet", "social media",
    "smartphone", "app", "online", "neuroscience", "neurotransmitter",
    "capitalism", "gdp", "productivity", "optimize", "optimization",
    "quantum", "evolution", "genes", "serotonin", "feedback loop",
]

# Safety patterns by category (design §19). self_harm is high_risk.
SAFETY_PATTERNS = {
    "medical": (r"\b(diagnos\w*|prescrib\w*|medication|you should take|take \d+ ?mg)\b",
                "high", "Remove medical advice; an interpretive persona must not diagnose."),
    "legal_financial": (r"\b(guaranteed returns?|invest in|file a lawsuit|sue (?:them|him|her))\b",
                        "high", "Remove legal/financial advice."),
    "self_harm": (r"\b(kill yourself|harm yourself|end your life)\b",
                  "high", "Remove self-harm content."),
    "religious_authority": (r"\b(the one true|only true path|i am the real)\b",
                            "high", "Persona must not claim religious authority or to be the real figure."),
}

Warning = Dict[str, Any]


def _w(seg: Dict[str, Any], severity: str, message: str, **extra) -> Warning:
    return {"segment_id": seg["id"], "segment_index": seg["segment_index"],
            "speaker_label": seg["speaker_label"], "severity": severity,
            "message": message, **extra}


def anachronism_check(segs: List[Dict[str, Any]]) -> Tuple[float, List[Warning]]:
    warnings: List[Warning] = []
    guests = [s for s in segs if s["role"] != "host"]
    for s in guests:
        low = s["text"].lower()
        for term in MODERN_TERMS:
            if re.search(r"\b" + re.escape(term) + r"\b", low):
                warnings.append(_w(s, "high",
                                   f"{s['speaker_label']} uses the modern term '{term}'.",
                                   suggested_action="Let the host say it, or use a period image."))
                break
    score = 1.0 if not guests else round(1 - len(warnings) / len(guests), 3)
    return score, warnings


def safety_check(segs: List[Dict[str, Any]]) -> Tuple[float, List[Warning], bool]:
    warnings: List[Warning] = []
    high_risk = False
    for s in segs:
        low = s["text"].lower()
        for cat, (pat, sev, action) in SAFETY_PATTERNS.items():
            if re.search(pat, low):
                warnings.append(_w(s, sev, f"Safety ({cat}): possible disallowed content.",
                                   suggested_action=action))
                if cat == "self_harm":
                    high_risk = True
    score = 1.0 if not segs else round(1 - len(warnings) / len(segs), 3)
    return score, warnings, high_risk


def dialogue_quality_check(segs: List[Dict[str, Any]]) -> Tuple[float, List[Warning]]:
    warnings: List[Warning] = []
    if not any(s["role"] == "host" for s in segs):
        warnings.append(_w(segs[0], "high", "The host never speaks; nobody guides the listener."))
    # 3+ consecutive segments from the same speaker = monologue.
    run = 1
    for i in range(1, len(segs)):
        if segs[i]["speaker_label"] == segs[i - 1]["speaker_label"]:
            run += 1
            if run == 3:
                warnings.append(_w(segs[i], "medium",
                                   f"{segs[i]['speaker_label']} speaks 3+ turns in a row (monologue)."))
        else:
            run = 1
    # exact-duplicate lines = repetition.
    seen: Dict[str, int] = defaultdict(int)
    for s in segs:
        key = s["text"].strip().lower()
        seen[key] += 1
        if seen[key] == 2:
            warnings.append(_w(s, "low", "This line repeats an earlier line verbatim."))
    score = round(max(0.0, 1 - 0.1 * len(warnings)), 3)
    return score, warnings


def audio_readiness_check(segs: List[Dict[str, Any]]) -> Tuple[float, List[Warning]]:
    warnings: List[Warning] = []
    for s in segs:
        wc = len(s["text"].split())
        if wc > 80:
            warnings.append(_w(s, "low", f"Segment is long ({wc} words); split for natural delivery.",
                               suggested_action="Split into two segments."))
        if re.search(r"[\[\]\(\){}<>]", s["text"]):
            warnings.append(_w(s, "low", "Brackets/symbols may be read aloud by TTS; remove them.",
                               suggested_action="Strip stage-direction symbols."))
    score = round(max(0.0, 1 - 0.05 * len(warnings)), 3)
    return score, warnings


# --- distinctiveness (engineered, not LLM) ----------------------------------

def _cos(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5 or 1.0
    nb = sum(y * y for y in b) ** 0.5 or 1.0
    return dot / (na * nb)


def _centroid(vecs: List[List[float]]) -> List[float]:
    n = len(vecs)
    dim = len(vecs[0])
    return [sum(v[i] for v in vecs) / n for i in range(dim)]


def distinctiveness_check(segs: List[Dict[str, Any]], embedder) -> Tuple[float, List[Warning]]:
    """Score how distinguishable speakers are by their lines.

    Embeds every segment, builds a per-speaker centroid, and reports the mean
    pairwise cosine *distance* between speaker centroids (0 = identical voices,
    1 ~ unrelated). Also flags any segment that sits closer to another speaker's
    centroid than its own — the "could you tell who said this?" failure.
    """
    by_speaker: Dict[str, List[List[float]]] = defaultdict(list)
    vecs = embedder.embed([s["text"] for s in segs])
    for s, v in zip(segs, vecs):
        by_speaker[s["speaker_label"]].append(v)
    speakers = list(by_speaker)
    if len(speakers) < 2:
        return 1.0, []
    centroids = {sp: _centroid(by_speaker[sp]) for sp in speakers}

    dists = []
    for i in range(len(speakers)):
        for j in range(i + 1, len(speakers)):
            dists.append(1 - _cos(centroids[speakers[i]], centroids[speakers[j]]))
    score = round(max(0.0, min(1.0, sum(dists) / len(dists))), 3)

    warnings: List[Warning] = []
    for s, v in zip(segs, vecs):
        own = _cos(v, centroids[s["speaker_label"]])
        nearest_other = max(_cos(v, centroids[sp]) for sp in speakers
                            if sp != s["speaker_label"])
        if nearest_other > own:
            warnings.append(_w(s, "medium",
                               f"This line reads more like another speaker than {s['speaker_label']}.",
                               suggested_action="Sharpen the persona's voice."))
    if score < 0.2:
        warnings.append({"segment_id": None, "segment_index": None, "speaker_label": None,
                         "severity": "high",
                         "message": f"Speakers are nearly interchangeable (distinctiveness {score})."})
    return score, warnings
