"""Trace writer for read-only shadow ingestion."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .event_log import write_events


def write_shadow_trace(
    path: str | Path, events: Iterable[Mapping[str, Any]]
) -> None:
    write_events(path, events)


def warning_event(reason: str) -> dict[str, Any]:
    return {
        "event_type": "shadow_warning_detected",
        "status": "warning",
        "reason": reason,
    }
