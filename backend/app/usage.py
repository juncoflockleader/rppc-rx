"""Cost + debug-trace logging (design §20.3-20.4).

Best-effort: a failed insert never breaks the actual LLM/TTS call. A contextvar
carries the current project/episode (set per job) so usage rows can be attributed
without threading ids through every function.
"""
from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional, Tuple

log = logging.getLogger("usage")

_ctx: ContextVar[Tuple[Optional[str], Optional[str]]] = ContextVar("usage_ctx",
                                                                   default=(None, None))


@contextmanager
def using_context(project_id: Optional[str], episode_id: Optional[str]):
    token = _ctx.set((project_id, episode_id))
    try:
        yield
    finally:
        _ctx.reset(token)


def _insert(kind: str, **fields) -> None:
    project_id, episode_id = _ctx.get()
    try:
        from .db import get_conn

        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO usage_events
                    (kind, task_name, prompt_version, model, input_tokens,
                     output_tokens, char_count, duration_ms, latency_ms,
                     project_id, episode_id, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (kind, fields.get("task_name"), fields.get("prompt_version"),
                 fields.get("model"), fields.get("input_tokens"),
                 fields.get("output_tokens"), fields.get("char_count"),
                 fields.get("duration_ms"), fields.get("latency_ms"),
                 project_id, episode_id,
                 json.dumps(fields.get("metadata")) if fields.get("metadata") else None),
            )
    except Exception:  # noqa: BLE001 — telemetry must never break the request
        log.debug("usage insert skipped", exc_info=True)


def record_llm(task_name: str, prompt_version: str, model: str,
               input_tokens: int, output_tokens: int, latency_ms: int) -> None:
    _insert("llm", task_name=task_name, prompt_version=prompt_version, model=model,
            input_tokens=input_tokens, output_tokens=output_tokens, latency_ms=latency_ms)


def record_tts(model: str, char_count: int, duration_ms: int, latency_ms: int) -> None:
    _insert("tts", model=model, char_count=char_count, duration_ms=duration_ms,
            latency_ms=latency_ms)
