from app.export import builder
from app.notices import DISCLAIMER_EN, notices

EPISODE = {"id": "e1", "title": "Desire", "settings": {"goal": "Understand desire"}}
SEGS = [
    {"segment_index": 1, "speaker_label": "HOST", "text": "Welcome.",
     "evidence": [{"type": "host_bridge", "claim_id": None, "concept": None}],
     "duration_ms": 2000},
    {"segment_index": 2, "speaker_label": "LAOZI", "text": "Water yields.",
     "evidence": [{"type": "persona_canon", "claim_id": None, "concept": "wu wei"},
                  {"type": "source_material", "claim_id": "c1", "concept": None}],
     "duration_ms": 3000},
]


def test_transcript_md_includes_disclaimer_and_speakers():
    md = builder.transcript_md(EPISODE, SEGS)
    assert DISCLAIMER_EN in md
    assert "**HOST:** Welcome." in md and "**LAOZI:** Water yields." in md


def test_srt_timecodes_are_sequential():
    srt = builder.transcript_srt(SEGS)
    assert "00:00:00,000 --> 00:00:02,000" in srt
    assert "00:00:02,000 --> 00:00:05,000" in srt  # 2s then +3s


def test_show_notes_has_cast_themes_takeaway_and_notices():
    notes = builder.show_notes_md(
        EPISODE, ["desire", "comparison"], "Less forcing.",
        [{"speaker_label": "HOST", "persona_id": "modern_host"}])
    assert "desire, comparison" in notes
    assert "Less forcing." in notes
    assert DISCLAIMER_EN in notes


def test_evidence_report_resolves_claim_text():
    rep = builder.evidence_report(EPISODE, SEGS, {"c1": "Desire is amplified by comparison."})
    seg2 = rep["segments"][1]
    src = [e for e in seg2["evidence"] if e["type"] == "source_material"][0]
    assert src["claim_text"] == "Desire is amplified by comparison."
    assert rep["disclaimer"] == DISCLAIMER_EN


def test_notices_payload():
    n = notices()
    assert n["disclaimer_en"] and n["disclaimer_zh"] and n["source_copyright"]
