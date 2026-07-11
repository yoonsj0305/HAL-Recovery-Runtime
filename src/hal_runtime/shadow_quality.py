"""Quality semantics for read-only shadow observations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Any

from .shadow_models import ShadowObservation, shadow_boundary_fields


QUALITY_BANDS = ("high", "medium", "low", "insufficient")
FIELD_GROUPS = {
    "required_like_fields": ("tile_id", "observed_status", "role"),
    "measurement_fields": (
        "measurement_name",
        "measurement_value",
        "measurement_unit",
        "threshold_min",
        "threshold_max",
        "pass_fail",
    ),
    "identity_fields": ("profile_id", "die_id", "wafer_id", "lot_id"),
    "spatial_fields": ("x", "y"),
}
OBSERVATION_COVERAGE_FIELDS = (
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
)


def build_observation_quality(observation: ShadowObservation) -> dict[str, Any]:
    """Return evidence-quality metadata for a normalized observation."""

    has_measurement = observation.measurement_value is not None
    has_thresholds = (
        observation.threshold_min is not None and observation.threshold_max is not None
    )
    has_explicit_pass_fail = observation.pass_fail in {"pass", "fail"}
    has_coordinates = observation.x is not None and observation.y is not None
    has_role = observation.role != "unknown"
    has_timestamp = observation.timestamp is not None
    score = observation.confidence
    reasons: list[str] = []
    warnings: list[str] = []
    if has_measurement and has_thresholds:
        reasons.append("measurement_with_thresholds")
    elif has_measurement:
        reasons.append("measurement_without_complete_thresholds")
    if has_explicit_pass_fail:
        reasons.append("explicit_pass_fail_present")
    if observation.observed_status != "unknown":
        reasons.append("observed_status_present")
    if observation.tile_id is None:
        warnings.append("missing_tile_id")
        score = min(score, 0.2)
    if not has_role:
        warnings.append("missing_role_defaulted_unknown")
    if observation.observed_status == "unknown":
        warnings.append("missing_observed_status_defaulted_unknown")
        score = min(score, 0.3 if observation.tile_id else 0.2)
    if has_explicit_pass_fail and not has_thresholds:
        score = min(score, 0.6)
    if observation.observed_status != "unknown" and not has_explicit_pass_fail and not (
        has_measurement and has_thresholds
    ):
        score = min(score, 0.4)
    score = min(score, 0.9)
    score = _clamp(score)
    field_coverage = _observation_field_coverage(observation)
    return {
        "quality_score": score,
        "quality_band": quality_band(score),
        "field_coverage": field_coverage,
        "has_measurement": has_measurement,
        "has_thresholds": has_thresholds,
        "has_explicit_pass_fail": has_explicit_pass_fail,
        "has_coordinates": has_coordinates,
        "has_role": has_role,
        "has_timestamp": has_timestamp,
        "quality_reasons": sorted(dict.fromkeys(reasons)),
        "quality_warnings": sorted(dict.fromkeys(warnings)),
    }


def add_conflict_quality_warnings(
    observations: tuple[ShadowObservation, ...],
    conflict_matrix: dict[str, Any],
) -> tuple[ShadowObservation, ...]:
    warning_by_tile = {
        str(item["tile_id"]): str(item["warning"])
        for item in conflict_matrix.get("conflicting_tiles", [])
        if isinstance(item, dict) and item.get("tile_id") and item.get("warning")
    }
    if not warning_by_tile:
        return observations
    updated: list[ShadowObservation] = []
    for observation in observations:
        quality = dict(observation.observation_quality)
        warnings = list(quality.get("quality_warnings", []))
        warning = warning_by_tile.get(str(observation.tile_id))
        if warning:
            warnings.append(warning)
            score = min(float(quality.get("quality_score", 0.0)), 0.6)
            quality["quality_score"] = _clamp(score)
            quality["quality_band"] = quality_band(score)
            quality["quality_warnings"] = sorted(dict.fromkeys(warnings))
        updated.append(replace(observation, observation_quality=quality))
    return tuple(updated)


def build_field_coverage(
    observations: tuple[ShadowObservation, ...] | list[ShadowObservation],
) -> dict[str, Any]:
    denominator = len(observations)
    result: dict[str, Any] = {}
    total_present = 0
    total_possible = 0
    for group_name, fields in FIELD_GROUPS.items():
        group: dict[str, float] = {}
        for field in fields:
            present = sum(1 for observation in observations if _field_present(observation, field))
            total_present += present
            total_possible += denominator
            group[field] = _fraction(present, denominator)
        result[group_name] = group
    result["overall_field_coverage"] = _fraction(total_present, total_possible)
    return result


def field_coverage_warnings(field_coverage: dict[str, Any]) -> tuple[str, ...]:
    warnings: list[str] = []
    for group_name in FIELD_GROUPS:
        group = field_coverage.get(group_name, {})
        if not isinstance(group, dict) or not group:
            continue
        values = [float(value) for value in group.values() if isinstance(value, int | float)]
        average = sum(values) / len(values) if values else 0.0
        if average < 0.5:
            warnings.append(f"low_field_coverage:{group_name}")
    return tuple(sorted(warnings))


def build_conflict_matrix(
    observations: tuple[ShadowObservation, ...] | list[ShadowObservation],
) -> dict[str, Any]:
    by_tile: dict[str, list[ShadowObservation]] = defaultdict(list)
    for observation in observations:
        if observation.tile_id:
            by_tile[observation.tile_id].append(observation)
    conflicts: list[dict[str, Any]] = []
    summary = {
        "status_conflicts": 0,
        "role_conflicts": 0,
        "measurement_conflicts": 0,
        "identity_conflicts": 0,
    }
    for tile_id in sorted(by_tile):
        tile_observations = by_tile[tile_id]
        statuses = _values(
            observation.observed_status
            for observation in tile_observations
            if observation.observed_status != "unknown"
        )
        pass_fail_values = _values(
            observation.pass_fail
            for observation in tile_observations
            if observation.pass_fail != "unknown"
        )
        roles = _values(
            observation.role
            for observation in tile_observations
            if observation.role != "unknown"
        )
        measurements = _values(
            f"{observation.measurement_name}:{observation.measurement_value}"
            for observation in tile_observations
            if observation.measurement_name and observation.measurement_value is not None
        )
        identities = _values(
            ":".join(
                str(value)
                for value in (
                    observation.profile_id,
                    observation.die_id,
                    observation.wafer_id,
                    observation.lot_id,
                )
                if value is not None
            )
            for observation in tile_observations
        )
        conflict_type = ""
        if len(statuses) > 1 or len(pass_fail_values) > 1:
            conflict_type = "status_conflict"
            summary["status_conflicts"] += 1
        elif len(roles) > 1:
            conflict_type = "role_conflict"
            summary["role_conflicts"] += 1
        elif len(measurements) > 1:
            conflict_type = "measurement_conflict"
            summary["measurement_conflicts"] += 1
        elif len(identities) > 1:
            conflict_type = "identity_conflict"
            summary["identity_conflicts"] += 1
        if not conflict_type:
            continue
        conflicts.append(
            {
                "tile_id": tile_id,
                "observed_statuses": statuses,
                "pass_fail_values": pass_fail_values,
                "failure_types": _values(
                    observation.failure_type
                    for observation in tile_observations
                    if observation.failure_type != "unknown"
                ),
                "roles": roles,
                "source_files": _values(observation.source_file for observation in tile_observations),
                "conflict_type": conflict_type,
                "resolution": "candidate_status_degraded",
                "warning": f"conflicting_observations:{tile_id}",
            }
        )
    return {
        "conflict_count": len(conflicts),
        "conflicting_tiles": conflicts,
        "conflict_summary": summary,
    }


def conflict_warnings(conflict_matrix: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(item["warning"])
            for item in conflict_matrix.get("conflicting_tiles", [])
            if isinstance(item, dict) and item.get("warning")
        )
    )


def build_candidate_confidence_summary(
    candidate: dict[str, Any],
    warnings: tuple[str, ...] | list[str] = (),
) -> dict[str, Any]:
    tiles = [tile for tile in candidate.get("tiles", []) if isinstance(tile, dict)]
    confidences = [
        float(tile.get("confidence", 0.0))
        for tile in tiles
        if isinstance(tile.get("confidence", 0.0), int | float)
    ]
    band_counts = {band: 0 for band in QUALITY_BANDS}
    for confidence in confidences:
        band_counts[quality_band(confidence)] += 1
    return {
        "candidate_tile_count": len(tiles),
        "average_tile_confidence": _fraction(sum(confidences), len(confidences)),
        "min_tile_confidence": _clamp(min(confidences) if confidences else 0.0),
        "max_tile_confidence": _clamp(max(confidences) if confidences else 0.0),
        "confidence_band_counts": band_counts,
        "candidate_quality_warnings": sorted(dict.fromkeys(warnings)),
        "safe_for_pipeline_handoff": False,
        "requires_human_review": True,
    }


def build_shadow_quality_report(
    *,
    profile_id: str,
    observations: tuple[ShadowObservation, ...],
    field_coverage: dict[str, Any],
    conflict_matrix: dict[str, Any],
    candidate_confidence_summary: dict[str, Any],
    quality_warning_reasons: tuple[str, ...] | list[str],
    quality_blocking_reasons: tuple[str, ...] | list[str],
) -> dict[str, Any]:
    scores = [
        float(observation.observation_quality.get("quality_score", 0.0))
        for observation in observations
    ]
    score = _fraction(sum(scores), len(scores)) if scores else 0.0
    band_counts = {band: 0 for band in QUALITY_BANDS}
    for value in scores:
        band_counts[quality_band(value)] += 1
    if quality_blocking_reasons:
        status = "shadow_quality_blocked"
    elif not observations or quality_band(score) == "insufficient":
        status = "shadow_quality_insufficient"
    elif quality_warning_reasons:
        status = "shadow_quality_computed_with_warnings"
    else:
        status = "shadow_quality_computed"
    return {
        **shadow_boundary_fields(),
        "profile_id": profile_id,
        "shadow_quality_status": status,
        "shadow_quality_score": score,
        "shadow_quality_band": quality_band(score),
        "observation_count": len(observations),
        "quality_band_counts": band_counts,
        "field_coverage": field_coverage,
        "conflict_matrix": conflict_matrix,
        "candidate_confidence_summary": candidate_confidence_summary,
        "quality_reasons": ["shadow_quality_computed_from_read_only_observations"],
        "quality_warning_reasons": sorted(dict.fromkeys(quality_warning_reasons)),
        "quality_blocking_reasons": sorted(dict.fromkeys(quality_blocking_reasons)),
        "known_limitations": [
            "quality_score_is_not_hardware_safety",
            "read_only_file_ingestion",
            "not_certification",
            "candidate_profile_requires_human_review",
        ],
    }


def quality_warning_reasons(
    observations: tuple[ShadowObservation, ...],
    field_coverage: dict[str, Any],
    conflict_matrix: dict[str, Any],
) -> tuple[str, ...]:
    warnings: list[str] = list(field_coverage_warnings(field_coverage))
    warnings.extend(conflict_warnings(conflict_matrix))
    for observation in observations:
        tile_id = observation.tile_id or "unknown_tile"
        quality = observation.observation_quality
        band = quality.get("quality_band")
        if band == "insufficient":
            warnings.append(f"insufficient_observation_quality:{tile_id}")
        elif band == "low":
            warnings.append(f"low_observation_quality:{tile_id}")
    return tuple(sorted(dict.fromkeys(warnings)))


def quality_band(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "medium"
    if score >= 0.25:
        return "low"
    return "insufficient"


def _observation_field_coverage(observation: ShadowObservation) -> float:
    present = sum(
        1 for field in OBSERVATION_COVERAGE_FIELDS if _field_present(observation, field)
    )
    return _fraction(present, len(OBSERVATION_COVERAGE_FIELDS))


def _field_present(observation: ShadowObservation, field: str) -> bool:
    value = getattr(observation, field)
    if value is None:
        return False
    if isinstance(value, str) and not value:
        return False
    if field in {"role", "observed_status", "pass_fail", "failure_type"}:
        return value != "unknown"
    return True


def _values(values) -> list[str]:
    return sorted(dict.fromkeys(str(value) for value in values if value is not None))


def _fraction(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return _clamp(numerator / denominator)


def _clamp(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return round(float(value), 2)
