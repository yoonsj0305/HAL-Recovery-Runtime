"""Trace writer for the simulation-only pipeline runner."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .event_log import write_events


def pipeline_started_event(input_mode: str) -> dict[str, Any]:
    return {
        "event_type": "pipeline_started",
        "status": "ok",
        "input_mode": input_mode,
    }


def stage_started_event(stage_name: str) -> dict[str, Any]:
    return {
        "event_type": "pipeline_stage_started",
        "status": "ok",
        "stage_name": stage_name,
    }


def stage_completed_event(stage_name: str, status: str = "ok") -> dict[str, Any]:
    return {
        "event_type": "pipeline_stage_completed",
        "status": status,
        "stage_name": stage_name,
    }


def stage_warning_event(stage_name: str, reason: str) -> dict[str, Any]:
    return {
        "event_type": "pipeline_stage_warning",
        "status": "warning",
        "stage_name": stage_name,
        "reason": reason,
    }


def stage_failed_event(stage_name: str, status: str, reason: str) -> dict[str, Any]:
    return {
        "event_type": "pipeline_stage_failed",
        "status": status,
        "stage_name": stage_name,
        "reason": reason,
    }


def stage_skipped_event(stage_name: str, reason: str) -> dict[str, Any]:
    return {
        "event_type": "pipeline_stage_skipped",
        "status": "skipped",
        "stage_name": stage_name,
        "reason": reason,
    }


def pipeline_completed_event(pipeline_status: str) -> dict[str, Any]:
    return {
        "event_type": "pipeline_completed",
        "status": "ok" if pipeline_status.startswith("pipeline_completed") else "blocked",
        "pipeline_status": pipeline_status,
    }


def terminal_state_event(
    *, pipeline_terminal_stage: str, pipeline_exit_reason: str, status: str
) -> dict[str, Any]:
    return {
        "event_type": "pipeline_terminal_state_recorded",
        "status": status,
        "pipeline_terminal_stage": pipeline_terminal_stage,
        "pipeline_exit_reason": pipeline_exit_reason,
    }


def consistency_checked_event(status: str = "ok") -> dict[str, Any]:
    return {"event_type": "pipeline_consistency_checked", "status": status}


def write_pipeline_trace(
    path: str | Path, events: Iterable[Mapping[str, Any]]
) -> None:
    write_events(path, events)
