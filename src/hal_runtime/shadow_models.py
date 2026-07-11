"""Data models for read-only shadow ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .models import RUNTIME_VERSION


SHADOW_INGESTION_VERSION = RUNTIME_VERSION
SHADOW_QUALITY_SEMANTICS_VERSION = RUNTIME_VERSION
DEFAULT_PROFILE_ID = "SHADOW_PROFILE_001"
READ_ONLY_LIMITATIONS = (
    "read_only_file_ingestion",
    "not_hardware_control",
    "not_certification",
    "profile_candidate_requires_human_review",
)


@dataclass(frozen=True)
class ShadowObservation:
    profile_id: str
    die_id: str | None
    wafer_id: str | None
    lot_id: str | None
    tile_id: str | None
    x: int | float | None
    y: int | float | None
    role: str
    observed_status: str
    failure_type: str
    measurement_name: str | None
    measurement_value: int | float | None
    measurement_unit: str | None
    threshold_min: int | float | None
    threshold_max: int | float | None
    pass_fail: str
    timestamp: str | None
    source_file: str
    source_row: int
    confidence: float
    observation_quality: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "die_id": self.die_id,
            "wafer_id": self.wafer_id,
            "lot_id": self.lot_id,
            "tile_id": self.tile_id,
            "x": self.x,
            "y": self.y,
            "role": self.role,
            "observed_status": self.observed_status,
            "failure_type": self.failure_type,
            "measurement_name": self.measurement_name,
            "measurement_value": self.measurement_value,
            "measurement_unit": self.measurement_unit,
            "threshold_min": self.threshold_min,
            "threshold_max": self.threshold_max,
            "pass_fail": self.pass_fail,
            "timestamp": self.timestamp,
            "source_file": self.source_file,
            "source_row": self.source_row,
            "confidence": self.confidence,
            "observation_quality": self.observation_quality,
        }


@dataclass(frozen=True)
class ShadowRawRow:
    source_file: str
    source_row: int
    values: dict[str, Any]


@dataclass(frozen=True)
class ShadowReadResult:
    rows: tuple[ShadowRawRow, ...]
    files_discovered: tuple[str, ...]
    files_supported: tuple[str, ...]
    files_ignored: tuple[str, ...] = ()
    files_skipped: tuple[str, ...] = ()
    warning_reasons: tuple[str, ...] = ()
    invalid_reasons: tuple[str, ...] = ()
    safety_boundary_violations: tuple[str, ...] = ()
    events: tuple[dict[str, Any], ...] = ()


def shadow_boundary_fields() -> dict[str, Any]:
    return {
        "runtime_version": RUNTIME_VERSION,
        "shadow_ingestion_version": SHADOW_INGESTION_VERSION,
        "shadow_quality_semantics_version": SHADOW_QUALITY_SEMANTICS_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "read_only": True,
    }
