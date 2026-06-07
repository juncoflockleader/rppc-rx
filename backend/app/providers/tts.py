"""TTS provider adapter (design §7, §11.9).

Business code renders audio through `TTSProvider`, never a vendor SDK. The
deterministic `FakeTTSProvider` emits valid PCM-WAV silence sized to the
segment's estimated duration — enough to exercise rendering, stitching, mixing,
and re-render end to end with no network or audio toolchain. Real vendors
(ElevenLabs, etc.) implement the same interface later.
"""
from __future__ import annotations

import io
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..config import get_settings


@dataclass
class TTSRequest:
    speaker_label: str
    voice_id: str
    text: str
    estimated_seconds: int = 5
    delivery: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSResult:
    audio: bytes
    duration_ms: int
    sample_rate: int
    format: str  # wav | mp3 | ...


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, req: TTSRequest) -> TTSResult:
        ...


class FakeTTSProvider(TTSProvider):
    """Deterministic silent-WAV renderer. Duration tracks estimated_seconds."""

    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate

    def synthesize(self, req: TTSRequest) -> TTSResult:
        seconds = max(0.5, float(req.estimated_seconds or 1))
        n_frames = int(self.sample_rate * seconds)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)            # 16-bit PCM
            w.setframerate(self.sample_rate)
            w.writeframes(b"\x00\x00" * n_frames)  # silence
        return TTSResult(audio=buf.getvalue(), duration_ms=int(seconds * 1000),
                         sample_rate=self.sample_rate, format="wav")


class NotImplementedTTSProvider(TTSProvider):
    def __init__(self, name: str) -> None:
        self._name = name

    def synthesize(self, req: TTSRequest) -> TTSResult:  # pragma: no cover
        raise NotImplementedError(
            f"TTS provider '{self._name}' is not wired yet; use TTS_PROVIDER=fake.")


_provider: Optional[TTSProvider] = None


def get_tts_provider() -> TTSProvider:
    global _provider
    if _provider is None:
        s = get_settings()
        if s.tts_provider == "fake":
            _provider = FakeTTSProvider(s.tts_sample_rate)
        else:
            _provider = NotImplementedTTSProvider(s.tts_provider)
    return _provider


def reset_tts_provider() -> None:
    global _provider
    _provider = None
