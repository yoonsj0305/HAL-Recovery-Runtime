"""Validation for read-only shadow ingestion artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .models import RUNTIME_VERSION
from .shadow_models import shadow_boundary_fields


UNSAFE_TRUE_FIELDS = (
    "hardware_control_enabled",
    "real_execution_allowed",
    "hardware_control_allowed",
    "certification_passed",
    "safe_for_" + "hardware_control",
    "apply_to_" + "device",
    "hardware_" + "execute",
)
SHADOW_REQUIRED_FILES = (
    "shadow_observations.json",
    "recovery_profile_candidate.json",
    "shadow_ingestion_report.json",
    "shadow_quality_report.json",
)


def unsafe_shadow_fields(payload: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        field
        for field in UNSAFE_TRUE_FIELDS
        if _truthy(payload.get(field))
    )


def validate_shadow_artifacts(directory: str | Path) -> dict[str, Any]:
    root = Path(directory)
    loaded: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    invalid_json: list[str] = []
    for name in SHADOW_REQUIRED_FILES:
        path = root / name
        if not path.is_file():
            missing.append(name)
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            invalid_json.append(name)
            continue
        if not isinstance(payload, dict):
            invalid_json.append(name)
            continue
        loaded[name] = payload

    warnings: list[str] = []
    violations: list[str] = []
    invalid_reasons: list[str] = []
    for name, payload in loaded.items():
        violations.extend(_boundary_violations(name, payload))
    candidate = loaded.get("recovery_profile_candidate.json", {})
    candidate_reasons = _candidate_invalid_reasons(candidate)
    if candidate_reasons:
        invalid_reasons.extend(candidate_reasons)
    report = loaded.get("shadow_ingestion_report.json", {})
    report_warnings = report.get("warning_reasons")
    if isinstance(report_warnings, list):
        warnings.extend(str(item) for item in report_warnings)
    quality_report = loaded.get("shadow_quality_report.json", {})
    quality_report_warnings = quality_report.get("quality_warning_reasons")
    if isinstance(quality_report_warnings, list):
        warnings.extend(str(item) for item in quality_report_warnings)
    observations = loaded.get("shadow_observations.json", {})
    observation_count = observations.get("observation_count", 0)
    observation_quality_reasons = _observation_quality_reasons(observations)
    field_coverage_reasons = _field_coverage_reasons(observations, quality_report)
    conflict_reasons = _conflict_reasons(observations, quality_report)
    matrix = _validation_matrix(
        missing=missing,
        invalid_json=invalid_json,
        violations=violations,
        candidate_reasons=invalid_reasons,
        observation_quality_reasons=observation_quality_reasons,
        field_coverage_reasons=field_coverage_reasons,
        conflict_reasons=conflict_reasons,
    )
    if missing:
        status = "invalid_missing_shadow_artifacts"
        reasons = [f"missing_shadow_artifact:{name}" for name in missing]
    elif invalid_json:
        status = "invalid_shadow_json"
        reasons = [f"invalid_shadow_json:{name}" for name in invalid_json]
    elif violations:
        status = "blocked_safety_boundary"
        reasons = [f"safety_boundary_violation:{reason}" for reason in dict.fromkeys(violations)]
    elif invalid_reasons:
        status = "invalid_candidate_profile"
        reasons = list(dict.fromkeys(invalid_reasons))
    elif observation_quality_reasons or field_coverage_reasons:
        status = "invalid_candidate_profile"
        reasons = list(dict.fromkeys(observation_quality_reasons + field_coverage_reasons))
    elif warnings or conflict_reasons:
        status = "valid_with_warnings"
        reasons = ["shadow_data_valid_with_warnings"]
    else:
        status = "valid_shadow_data"
        reasons = ["shadow_data_valid"]
    passed = status in {"valid_shadow_data", "valid_with_warnings"}
    return {
        **shadow_boundary_fields(),
        "shadow_data_loaded": not missing and not invalid_json,
        "shadow_validation_passed": passed,
        "shadow_validation_status": status,
        "observation_count": observation_count if isinstance(observation_count, int) else 0,
        "candidate_profile_present": "recovery_profile_candidate.json" in loaded,
        "candidate_profile_safe": not violations and not invalid_reasons,
        "shadow_quality_report_loaded": "shadow_quality_report.json" in loaded,
        "shadow_quality_score": quality_report.get("shadow_quality_score", 0.0),
        "shadow_quality_band": quality_report.get("shadow_quality_band", "insufficient"),
        "shadow_validation_matrix": matrix,
        "safety_boundary_violations": list(dict.fromkeys(violations)),
        "validation_reasons": reasons,
        "warning_reasons": sorted(dict.fromkeys(warnings + conflict_reasons)),
        "known_limitations": [
            "shadow_validation_only",
            "not_certification",
            "no_hardware_control",
            "candidate_profile_requires_human_review",
        ],
    }


def _boundary_violations(name: str, payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("simulation_only") is not True:
        violations.append(f"{name}.simulation_only")
    if payload.get("hardware_control_enabled") is not False:
        violations.append(f"{name}.hardware_control_enabled")
    if payload.get("claim_boundary") != CLAIM_BOUNDARY:
        violations.append(f"{name}.claim_boundary")
    if payload.get("read_only") is not True:
        violations.append(f"{name}.read_only")
    if payload.get("shadow_quality_semantics_version") != RUNTIME_VERSION:
        violations.append(f"{name}.shadow_quality_semantics_version")
    for field in unsafe_shadow_fields(payload):
        violations.append(f"{name}.{field}")
    return violations


def _candidate_invalid_reasons(candidate: dict[str, Any]) -> list[str]:
    if not candidate:
        return []
    reasons: list[str] = []
    if candidate.get("human_review_required") is not True:
        reasons.append("candidate_human_review_required_false")
    if candidate.get("hardware_execution_enabled") is not False:
        reasons.append("candidate_hardware_execution_enabled_true")
    if candidate.get("hardware_control_enabled") is not False:
        reasons.append("candidate_hardware_control_enabled_true")
    if candidate.get("claim_boundary") != CLAIM_BOUNDARY:
        reasons.append("candidate_claim_boundary_not_simulation_only_not_certified")
    if candidate.get("voltage_policy") != "no_hardware_control":
        reasons.append("candidate_voltage_policy_not_no_hardware_control")
    if candidate.get("runtime_loader_hint") != "simulation_only":
        reasons.append("candidate_runtime_loader_hint_not_simulation_only")
    if candidate.get("assigned_workloads") != []:
        reasons.append("candidate_assigned_workloads_not_allowed_v1_0_0")
    summary = candidate.get("candidate_confidence_summary")
    if not isinstance(summary, dict):
        reasons.append("candidate_confidence_summary_missing")
    else:
        if summary.get("safe_for_pipeline_handoff") is not False:
            reasons.append("candidate_safe_for_pipeline_handoff_not_false")
        if summary.get("requires_human_review") is not True:
            reasons.append("candidate_confidence_summary_requires_human_review_false")
    return reasons


def _observation_quality_reasons(observations: dict[str, Any]) -> list[str]:
    items = observations.get("observations")
    if not isinstance(items, list):
        return ["shadow_observations_missing_observations"]
    reasons: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            reasons.append(f"shadow_observation_invalid:{index}")
            continue
        quality = item.get("observation_quality")
        if not isinstance(quality, dict):
            reasons.append(f"observation_quality_missing:{index}")
            continue
        score = quality.get("quality_score")
        if not isinstance(score, int | float) or isinstance(score, bool) or not 0.0 <= score <= 1.0:
            reasons.append(f"observation_quality_score_invalid:{index}")
        if quality.get("quality_band") not in {"high", "medium", "low", "insufficient"}:
            reasons.append(f"observation_quality_band_invalid:{index}")
    return reasons


def _field_coverage_reasons(
    observations: dict[str, Any], quality_report: dict[str, Any]
) -> list[str]:
    reasons: list[str] = []
    for source_name, payload in (
        ("shadow_observations.json", observations),
        ("shadow_quality_report.json", quality_report),
    ):
        coverage = payload.get("field_coverage")
        if not isinstance(coverage, dict):
            reasons.append(f"{source_name}.field_coverage_missing")
            continue
        for path, value in _coverage_values(coverage):
            if not isinstance(value, int | float) or isinstance(value, bool) or not 0.0 <= value <= 1.0:
                reasons.append(f"{source_name}.field_coverage_invalid:{path}")
    return reasons


def _coverage_values(payload: dict[str, Any], prefix: str = ""):
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            yield from _coverage_values(value, path)
        else:
            yield path, value


def _conflict_reasons(
    observations: dict[str, Any], quality_report: dict[str, Any]
) -> list[str]:
    reasons: list[str] = []
    for payload in (observations, quality_report):
        matrix = payload.get("conflict_matrix")
        if not isinstance(matrix, dict):
            continue
        for item in matrix.get("conflicting_tiles", []):
            if isinstance(item, dict) and isinstance(item.get("warning"), str):
                reasons.append(item["warning"])
    return sorted(dict.fromkeys(reasons))


def _validation_matrix(
    *,
    missing: list[str],
    invalid_json: list[str],
    violations: list[str],
    candidate_reasons: list[str],
    observation_quality_reasons: list[str],
    field_coverage_reasons: list[str],
    conflict_reasons: list[str],
) -> dict[str, Any]:
    artifacts_reasons = [f"missing_shadow_artifact:{name}" for name in missing]
    json_reasons = [f"invalid_shadow_json:{name}" for name in invalid_json]
    safety_reasons = [f"safety_boundary_violation:{reason}" for reason in violations]
    return {
        "shadow_artifacts_present": _matrix_entry(not artifacts_reasons, artifacts_reasons),
        "json_validity": _matrix_entry(not json_reasons, json_reasons),
        "safety_boundary": _matrix_entry(not safety_reasons, safety_reasons, blocked=True),
        "candidate_invariants": _matrix_entry(not candidate_reasons, candidate_reasons),
        "observation_quality": _matrix_entry(
            not observation_quality_reasons, observation_quality_reasons
        ),
        "field_coverage": _matrix_entry(
            not field_coverage_reasons, field_coverage_reasons
        ),
        "conflict_detection": {
            "passed": True,
            "status": "warnings_present" if conflict_reasons else "ok",
            "reasons": conflict_reasons,
        },
    }


def _matrix_entry(
    passed: bool, reasons: list[str], *, blocked: bool = False
) -> dict[str, Any]:
    if passed:
        status = "ok"
    elif blocked:
        status = "blocked"
    else:
        status = "invalid"
    return {"passed": passed, "status": status, "reasons": list(dict.fromkeys(reasons))}


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False
