"""Minimal observability (design §20.1).

Business-event logging as structured log lines. M1 keeps it to stdout via the
logging module; a later milestone can fan these to a metrics/analytics sink
without changing call sites. Per §20.4, we never log full source text.
"""
from __future__ import annotations

import json
import logging
from typing import Any

_log = logging.getLogger("events")

# Known event names (design §20.1). Kept as a set so typos surface in tests.
EVENTS = {
    "project_created",
    "project_deleted",
    "source_uploaded",
    "source_processed",
    "discussion_plan_generated",
    "script_generated",
    "qa_completed",
    "audio_generated",
    "audio_exported",
    "segment_rewritten",
    "segment_rerendered",
    "feedback_submitted",
}


def emit(event: str, **fields: Any) -> None:
    """Emit a business event. Unknown event names are allowed but flagged."""
    if event not in EVENTS:
        _log.warning("unknown event name: %s", event)
    _log.info("event %s %s", event, json.dumps(fields, default=str))
