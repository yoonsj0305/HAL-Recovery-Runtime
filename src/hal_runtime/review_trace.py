"""Trace writer for candidate review gate operations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .event_log import write_events


def write_review_trace(
    path: str | Path, events: Iterable[Mapping[str, Any]]
) -> None:
    write_events(path, events)


def gate_event(gate_id: str, status: str, reasons: list[str] | tuple[str, ...]) -> dict[str, Any]:
    return {
        "event_type": "review_gate_evaluated",
        "status": status,
        "gate_id": gate_id,
        "reasons": list(reasons),
    }
