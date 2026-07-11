"""Build reports and artifacts for read-only shadow ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .event_log import write_json
from .shadow_models import ShadowObservation, shadow_boundary_fields
from .shadow_normalizer import normalize_shadow_rows
from .shadow_profile_builder import build_recovery_profile_candidate
from .shadow_quality import (
    add_conflict_quality_warnings,
    build_conflict_matrix,
    build_field_coverage,
    build_shadow_quality_report,
    quality_warning_reasons,
)
from .shadow_readers import read_shadow_directory
from .shadow_schema import shadow_schema_document
from .shadow_trace import warning_event, write_shadow_trace
from .shadow_validator import validate_shadow_artifacts


def ingest_shadow_data(
    input_directory: str | Path, output_directory: str | Path
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    read_result = read_shadow_directory(input_directory)
    observations, normalize_warnings, normalize_events = normalize_shadow_rows(
        read_result.rows
    )
    field_coverage = build_field_coverage(observations)
    conflict_matrix = build_conflict_matrix(observations)
    observations = add_conflict_quality_warnings(observations, conflict_matrix)
    candidate, candidate_warnings = build_recovery_profile_candidate(observations)
    quality_warnings = quality_warning_reasons(
        observations, field_coverage, conflict_matrix
    )
    blocking = _blocking_reasons(read_result, observations)
    quality_blocking = tuple(blocking)
    quality_report = build_shadow_quality_report(
        profile_id=observations[0].profile_id if observations else "SHADOW_PROFILE_001",
        observations=observations,
        field_coverage=field_coverage,
        conflict_matrix=conflict_matrix,
        candidate_confidence_summary=candidate["candidate_confidence_summary"],
        quality_warning_reasons=quality_warnings,
        quality_blocking_reasons=quality_blocking,
    )
    warnings = list(
        sorted(
            dict.fromkeys(
            list(read_result.warning_reasons)
            + list(normalize_warnings)
            + list(candidate_warnings)
            + list(quality_warnings)
            )
        )
    )
    status, validation_status = _statuses(read_result, observations, warnings, blocking)
    profile_id = observations[0].profile_id if observations else "SHADOW_PROFILE_001"
    observations_doc = _observations_document(
        profile_id, observations, field_coverage, conflict_matrix
    )
    report = _ingestion_report(
        input_directory,
        read_result,
        observations,
        candidate,
        quality_report,
        field_coverage,
        conflict_matrix,
        status,
        validation_status,
        warnings,
        blocking,
        list(quality_warnings),
        list(quality_blocking),
    )
    events = list(read_result.events)
    events.extend(normalize_events)
    events.append({"event_type": "shadow_field_coverage_computed", "status": "ok"})
    events.append(
        {
            "event_type": "shadow_conflict_matrix_built",
            "status": "ok",
            "conflict_count": conflict_matrix["conflict_count"],
        }
    )
    for item in conflict_matrix.get("conflicting_tiles", []):
        events.append(
            {
                "event_type": "shadow_conflict_detected",
                "status": "warning",
                "tile_id": item["tile_id"],
                "reason": item["warning"],
            }
        )
    events.append(
        {
            "event_type": "shadow_candidate_confidence_summary_built",
            "status": "ok",
        }
    )
    events.append(
        {
            "event_type": "shadow_quality_computed",
            "status": "ok" if not quality_blocking else "blocked",
            "shadow_quality_band": quality_report["shadow_quality_band"],
        }
    )
    for reason in warnings:
        events.append(warning_event(reason))
    for reason in quality_warnings:
        events.append(
            {
                "event_type": "shadow_quality_warning_detected",
                "status": "warning",
                "reason": reason,
            }
        )
    if not blocking:
        events.append({"event_type": "shadow_profile_candidate_built", "status": "ok"})
    elif status == "shadow_ingestion_invalid_input":
        events.append(
            {
                "event_type": "shadow_input_invalid",
                "status": "invalid",
                "reason": validation_status,
            }
        )
    events.append(
        {
            "event_type": "shadow_ingestion_completed",
            "status": (
                "blocked"
                if status == "shadow_ingestion_blocked"
                else "invalid"
                if status == "shadow_ingestion_invalid_input"
                else "ok"
            ),
            "shadow_ingestion_status": status,
        }
    )
    write_json(output / "shadow_schema.json", shadow_schema_document())
    write_json(output / "shadow_observations.json", observations_doc)
    write_json(output / "recovery_profile_candidate.json", candidate)
    write_json(output / "shadow_ingestion_report.json", report)
    write_json(output / "shadow_quality_report.json", quality_report)
    write_shadow_trace(output / "shadow_trace.jsonl", events)
    return report


def validate_shadow_data(
    source_directory: str | Path, output_directory: str | Path
) -> dict[str, Any]:
    report = validate_shadow_artifacts(source_directory)
    write_json(Path(output_directory) / "shadow_validation_report.json", report)
    return report


def _blocking_reasons(read_result, observations: tuple[ShadowObservation, ...]) -> list[str]:
    if read_result.safety_boundary_violations:
        return [f"safety_boundary_violation:{reason}" for reason in read_result.safety_boundary_violations]
    if not read_result.files_supported:
        return ["invalid_no_supported_files"]
    if read_result.invalid_reasons and not observations:
        return ["invalid_input_format"]
    if not observations:
        return ["invalid_no_valid_observations"]
    return []


def _statuses(read_result, observations, warnings, blocking) -> tuple[str, str]:
    if blocking and any(reason.startswith("safety_boundary_violation:") for reason in blocking):
        return "shadow_ingestion_blocked", "blocked_safety_boundary"
    if blocking:
        reason = blocking[0]
        validation = (
            "invalid_no_supported_files"
            if reason == "invalid_no_supported_files"
            else "invalid_input_format"
            if reason == "invalid_input_format"
            else "invalid_no_valid_observations"
        )
        return "shadow_ingestion_invalid_input", validation
    if warnings:
        return "shadow_ingestion_completed_with_warnings", "valid_with_warnings"
    return "shadow_ingestion_completed", "valid_shadow_data"


def _observations_document(
    profile_id: str,
    observations: tuple[ShadowObservation, ...],
    field_coverage: dict[str, Any],
    conflict_matrix: dict[str, Any],
) -> dict[str, Any]:
    return {
        **shadow_boundary_fields(),
        "profile_id": profile_id,
        "observation_count": len(observations),
        "field_coverage": field_coverage,
        "conflict_matrix": conflict_matrix,
        "observations": [observation.to_dict() for observation in observations],
        "known_limitations": [
            "read_only_observations",
            "not_certification",
            "not_hardware_control",
        ],
    }


def _ingestion_report(
    input_directory,
    read_result,
    observations: tuple[ShadowObservation, ...],
    candidate: dict[str, Any],
    quality_report: dict[str, Any],
    field_coverage: dict[str, Any],
    conflict_matrix: dict[str, Any],
    status: str,
    validation_status: str,
    warnings: list[str],
    blocking: list[str],
    quality_warnings: list[str],
    quality_blocking: list[str],
) -> dict[str, Any]:
    summary = _summary(candidate)
    return {
        **shadow_boundary_fields(),
        "input_directory": Path(input_directory).name,
        "shadow_ingestion_status": status,
        "shadow_validation_status": validation_status,
        "profile_id": candidate["profile_id"],
        "files_discovered": len(read_result.files_discovered),
        "files_supported": len(read_result.files_supported),
        "files_ignored": list(read_result.files_ignored),
        "files_skipped": list(read_result.files_skipped),
        "observation_count": len(observations),
        "valid_observations": len(observations),
        "invalid_observations": 0 if observations else len(read_result.invalid_reasons),
        "warning_reasons": sorted(dict.fromkeys(warnings)),
        "blocking_reasons": sorted(dict.fromkeys(blocking)),
        "safety_boundary_violations": list(read_result.safety_boundary_violations),
        "shadow_quality_score": quality_report["shadow_quality_score"],
        "shadow_quality_band": quality_report["shadow_quality_band"],
        "field_coverage_summary": field_coverage,
        "conflict_count": conflict_matrix["conflict_count"],
        "quality_warning_reasons": sorted(dict.fromkeys(quality_warnings)),
        "quality_blocking_reasons": sorted(dict.fromkeys(quality_blocking)),
        "summary": summary,
        "known_limitations": [
            "read_only_file_ingestion",
            "profile_candidate_not_validated_for_runtime_control",
            "not_certification",
            "no_hardware_control",
        ],
    }


def _summary(candidate: dict[str, Any]) -> dict[str, Any]:
    tiles = candidate.get("tiles", [])
    roles: dict[str, int] = {}
    for tile in tiles:
        role = tile.get("role")
        if isinstance(role, str):
            roles[role] = roles.get(role, 0) + 1
    return {
        "tiles_observed": len(tiles),
        "tiles_available": _status_count(tiles, "available"),
        "tiles_degraded": _status_count(tiles, "degraded"),
        "tiles_blocked": _status_count(tiles, "blocked"),
        "tiles_unknown": _status_count(tiles, "unknown"),
        "roles_observed": roles,
    }


def _status_count(tiles: list[dict[str, Any]], status: str) -> int:
    return sum(tile.get("status") == status for tile in tiles)
