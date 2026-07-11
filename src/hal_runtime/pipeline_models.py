"""Data models for the simulation-only end-to-end pipeline runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .models import RUNTIME_VERSION
from .pipeline_stages import PIPELINE_RUNNER_VERSION


PIPELINE_ID = "PIPELINE_001"
PIPELINE_REPORT_SEMANTICS_VERSION = RUNTIME_VERSION
PIPELINE_STATUS_VALUES = (
    "pipeline_completed",
    "pipeline_completed_with_warnings",
    "pipeline_blocked",
    "pipeline_failed",
    "pipeline_invalid_input",
)
STAGE_STATUS_VALUES = (
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "skipped",
)


@dataclass(frozen=True)
class PipelineStageResult:
    stage_name: str
    stage_status: str
    artifact_directory: str | None = None
    primary_artifacts: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    skip_reason: str | None = None
    block_reason: str | None = None
    failure_reason: str | None = None

    @property
    def stage_ran(self) -> bool:
        return self.stage_status != "skipped"

    @property
    def stage_skipped(self) -> bool:
        return self.stage_status == "skipped"

    @property
    def stage_blocked(self) -> bool:
        return self.stage_status == "blocked"

    @property
    def stage_failed(self) -> bool:
        return self.stage_status == "failed"

    @property
    def stage_warning(self) -> bool:
        return self.stage_status == "completed_with_warnings"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "stage_name": self.stage_name,
            "stage_status": self.stage_status,
            "stage_ran": self.stage_ran,
            "stage_skipped": self.stage_skipped,
            "stage_blocked": self.stage_blocked,
            "stage_failed": self.stage_failed,
            "stage_warning": self.stage_warning,
            "skip_reason": self.skip_reason if self.stage_skipped else None,
            "block_reason": self.block_reason if self.stage_blocked else None,
            "failure_reason": self.failure_reason if self.stage_failed else None,
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "artifact_directory": self.artifact_directory,
            "primary_artifacts": list(self.primary_artifacts),
        }
        return payload


@dataclass(frozen=True)
class PipelineRunResult:
    exit_code: int
    summary: dict[str, Any]
    report: dict[str, Any]
    artifact_index: dict[str, Any]
    trace_events: tuple[dict[str, Any], ...]


def boundary_fields() -> dict[str, Any]:
    return {
        "runtime_version": RUNTIME_VERSION,
        "pipeline_runner_version": PIPELINE_RUNNER_VERSION,
        "pipeline_report_semantics_version": PIPELINE_REPORT_SEMANTICS_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
