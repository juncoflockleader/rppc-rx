import io
import wave

from app.audio import mixer
from app.audio.voice_direction import build_delivery, voice_id_for
from app.providers.tts import FakeTTSProvider, TTSRequest


def _wav_seconds(b: bytes) -> float:
    with wave.open(io.BytesIO(b), "rb") as r:
        return r.getnframes() / r.getframerate()


def test_fake_tts_duration_tracks_estimate():
    tts = FakeTTSProvider(sample_rate=16000)
    res = tts.synthesize(TTSRequest(speaker_label="HOST", voice_id="v", text="hi",
                                    estimated_seconds=2))
    assert res.format == "wav" and res.duration_ms == 2000
    assert abs(_wav_seconds(res.audio) - 2.0) < 0.01


def test_mixer_concatenates_with_pause():
    tts = FakeTTSProvider(sample_rate=16000)
    a = tts.synthesize(TTSRequest("HOST", "v", "a", estimated_seconds=1)).audio
    b = tts.synthesize(TTSRequest("LAOZI", "v", "b", estimated_seconds=2)).audio
    final, duration_ms = mixer.stitch([(a, 500), (b, 0)])
    # 1000ms + 500ms pause + 2000ms = ~3500ms
    assert abs(duration_ms - 3500) < 50
    assert abs(_wav_seconds(final) - 3.5) < 0.05
    assert final[:4] == b"RIFF"  # valid WAV container


def test_voice_direction_from_profile_and_defaults():
    d = build_delivery({"tone": "calm", "pace": "slow", "emotional_range": "restrained",
                        "tts_hints": {"default_pause_after_ms": 700}})
    assert d["tone"] == "calm" and d["pace"] == "slow" and d["pause_after_ms"] == 700
    assert build_delivery({})["pause_after_ms"] == 400
    assert voice_id_for("laozi") == "voice_laozi_default"
