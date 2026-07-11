"""Write newline-delimited audit events for policy simulation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .event_log import write_events


def write_policy_trace(path: str | Path, events: Iterable[Mapping[str, Any]]) -> None:
    write_events(path, events)
