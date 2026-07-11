"""Fixed schema metadata for read-only shadow ingestion."""

from __future__ import annotations

from typing import Any

from .shadow_models import READ_ONLY_LIMITATIONS, shadow_boundary_fields


MAX_SHADOW_INPUT_BYTES = 5 * 1024 * 1024
SUPPORTED_SHADOW_FILES = (
    "wafer_map.csv",
    "tile_status.csv",
    "test_log.csv",
    "probe_results.csv",
    "wafer_map.json",
    "tile_status.json",
    "test_log.json",
    "probe_results.json",
    "test_log.jsonl",
    "probe_results.jsonl",
)
NORMALIZED_FIELDS = (
    "profile_id",
    "die_id",
    "wafer_id",
    "lot_id",
    "tile_id",
    "x",
    "y",
    "role",
    "observed_status",
    "failure_type",
    "measurement_name",
    "measurement_value",
    "measurement_unit",
    "threshold_min",
    "threshold_max",
    "pass_fail",
    "timestamp",
    "source_file",
    "source_row",
    "confidence",
    "observation_quality",
)
ALLOWED_OBSERVED_STATUSES = ("pass", "fail", "degraded", "unknown")
ALLOWED_PASS_FAIL = ("pass", "fail", "unknown")
ALLOWED_ROLES = (
    "compute_tile",
    "memory_tile",
    "routing_tile",
    "sensor_tile",
    "io_tile",
    "unknown",
)
ALLOWED_CANDIDATE_ROLES = (
    "compute_tile",
    "memory_tile",
    "routing_tile",
    "sensor_tile",
    "io_tile",
)
ALLOWED_FAILURE_TYPES = (
    "none",
    "open_circuit",
    "short_circuit",
    "timing_violation",
    "leakage_high",
    "power_high",
    "signal_integrity",
    "thermal_anomaly",
    "intermittent",
    "unknown",
)


def shadow_schema_document() -> dict[str, Any]:
    return {
        **shadow_boundary_fields(),
        "supported_files": list(SUPPORTED_SHADOW_FILES),
        "normalized_fields": list(NORMALIZED_FIELDS),
        "known_limitations": list(READ_ONLY_LIMITATIONS),
    }
