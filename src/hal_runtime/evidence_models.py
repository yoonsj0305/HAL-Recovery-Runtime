"""Data models for evidence collection, validation, and reporting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidenceArtifact:
    artifact_name: str
    artifact_type: str
    relative_path: str
    sha256: str
    size_bytes: int
    required: bool
    source_path: Path
    present: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_name": self.artifact_name,
            "artifact_type": self.artifact_type,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "required": self.required,
            "present": self.present,
        }


@dataclass(frozen=True)
class EvidenceCollection:
    source_directory: Path
    artifacts: tuple[EvidenceArtifact, ...]
    missing_required_artifacts: tuple[str, ...]
    unsupported_artifacts: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceCheck:
    validation_passed: bool
    validation_status: str
    profile_id: str | None
    parsed_artifacts: dict[str, dict[str, Any]]
    missing_optional_artifacts: tuple[str, ...]
    safety_boundary_violations: tuple[str, ...]
    consistency_warnings: tuple[str, ...]
    evidence_reasons: tuple[str, ...]
    evidence_validation_reasons: tuple[str, ...]
    evidence_warning_reasons: tuple[str, ...]
    evidence_failure_category: str
    evidence_validation_stage: str
    evidence_validation_matrix: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class EvidenceBuildOutcome:
    manifest: dict[str, Any]
    bundle: dict[str, Any]
    report: dict[str, Any]
    trace_events: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class EvidenceBundleValidationOutcome:
    report: dict[str, Any]
    trace_events: tuple[dict[str, Any], ...] = ()
