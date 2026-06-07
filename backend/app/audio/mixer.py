"""Stitch per-segment WAV audio into a final mix (design §11.9).

Stdlib `wave` only — no ffmpeg/pydub. Reads each segment's PCM frames, inserts
the segment's `pause_after_ms` as silence, and writes a single WAV. All fake
segments share params (mono/16-bit/16k); the first segment defines the format.
Loudness normalization is a no-op for silent fakes (real audio layer adds it).
"""
from __future__ import annotations

import io
import wave
from typing import List, Tuple


def stitch(parts: List[Tuple[bytes, int]]) -> Tuple[bytes, int]:
    """parts: list of (wav_bytes, pause_after_ms). Returns (final_wav, duration_ms)."""
    if not parts:
        raise ValueError("nothing to stitch")

    nchannels = sampwidth = framerate = None
    frames = bytearray()

    for wav_bytes, pause_ms in parts:
        with wave.open(io.BytesIO(wav_bytes), "rb") as r:
            if framerate is None:
                nchannels, sampwidth, framerate = r.getnchannels(), r.getsampwidth(), r.getframerate()
            frames += r.readframes(r.getnframes())
        if pause_ms:
            n_silence = int(framerate * (pause_ms / 1000.0))
            frames += b"\x00" * (n_silence * sampwidth * nchannels)

    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(nchannels)
        w.setsampwidth(sampwidth)
        w.setframerate(framerate)
        w.writeframes(bytes(frames))

    total_frames = len(frames) // (sampwidth * nchannels)
    duration_ms = int(total_frames / framerate * 1000)
    return out.getvalue(), duration_ms
