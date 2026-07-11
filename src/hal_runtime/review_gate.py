"""Evaluate candidate review gates without promotion."""

from __future__ import annotations

from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .review_models import REVIEW_GATE_IDS


def evaluate_review_gates(
    candidate: dict[str, Any],
    shadow_quality: dict[str, Any],
    shadow_observations: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], list[str], dict[str, Any]]:
    gate_map: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    blocking: list[str] = []

    schema_reasons = _candidate_schema_reasons(candidate)
    gate_map["candidate_schema_gate"] = _gate(
        "candidate_schema_gate", not schema_reasons, schema_reasons
    )
    blocking.extend(schema_reasons)

    safety_reasons = _candidate_safety_reasons(candidate)
    gate_map["candidate_safety_gate"] = _gate(
        "candidate_safety_gate", not safety_reasons, safety_reasons
    )
    blocking.extend(safety_reasons)

    quality_reasons, quality_warnings = _quality_reasons(shadow_quality)
    gate_map["shadow_quality_gate"] = _gate(
        "shadow_quality_gate",
        not quality_reasons,
        quality_warnings if quality_warnings else quality_reasons,
        warning=bool(quality_warnings and not quality_reasons),
    )
    blocking.extend(quality_reasons)
    warnings.extend(quality_warnings)

    conflict_warnings = _conflict_warnings(shadow_observations, shadow_quality)
    gate_map["conflict_review_gate"] = _gate(
        "conflict_review_gate",
        True,
        conflict_warnings,
        warning=bool(conflict_warnings),
    )
    warnings.extend(conflict_warnings)

    pending_reason = ["explicit_review_decision_required_for_promotion"]
    gate_map["human_review_decision_gate"] = {
        "gate_id": "human_review_decision_gate",
        "gate_status": "pending",
        "gate_required": True,
        "reasons": pending_reason,
    }

    matrix = {
        gate_id: {
            "passed": gate_map[gate_id]["gate_status"] in {"passed", "warnings_present"},
            "status": gate_map[gate_id]["gate_status"],
            "reasons": gate_map[gate_id]["reasons"],
        }
        for gate_id in REVIEW_GATE_IDS
    }
    matrix["human_review_decision_gate"]["passed"] = False
    return (
        [gate_map[gate_id] for gate_id in REVIEW_GATE_IDS],
        sorted(dict.fromkeys(warnings)),
        sorted(dict.fromkeys(blocking)),
        matrix,
    )


def candidate_safety_reasons(candidate: dict[str, Any]) -> list[str]:
    return _candidate_safety_reasons(candidate)


def _gate(
    gate_id: str, passed: bool, reasons: list[str], *, warning: bool = False
) -> dict[str, Any]:
    status = "passed" if passed else "blocked"
    if warning:
        status = "warnings_present"
    return {
        "gate_id": gate_id,
        "gate_status": status,
        "gate_required": True,
        "reasons": sorted(dict.fromkeys(reasons)),
    }


def _candidate_schema_reasons(candidate: dict[str, Any]) -> list[str]:
    required = (
        "profile_id",
        "profile_candidate",
        "human_review_required",
        "hardware_execution_enabled",
        "runtime_loader_hint",
        "voltage_policy",
        "assigned_workloads",
        "unassigned_workloads",
        "preferred_routes",
        "blocked_roles",
        "allowed_roles",
    )
    reasons = [f"candidate_missing_required_field:{field}" for field in required if field not in candidate]
    for field in ("assigned_workloads", "unassigned_workloads", "preferred_routes", "blocked_roles", "allowed_roles"):
        if field in candidate and not isinstance(candidate[field], list):
            reasons.append(f"candidate_field_must_be_list:{field}")
    if candidate.get("profile_candidate") is not True:
        reasons.append("candidate_profile_candidate_not_true")
    return reasons


def _candidate_safety_reasons(candidate: dict[str, Any]) -> list[str]:
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
    return reasons


def _quality_reasons(shadow_quality: dict[str, Any]) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    warnings: list[str] = []
    status = shadow_quality.get("shadow_quality_status")
    band = shadow_quality.get("shadow_quality_band")
    score = shadow_quality.get("shadow_quality_score")
    if status == "shadow_quality_blocked":
        blocking.append("shadow_quality_blocked")
    if band == "insufficient" or not isinstance(score, int | float) or score < 0.25:
        blocking.append("shadow_quality_insufficient_for_review")
    warning_reasons = shadow_quality.get("quality_warning_reasons", [])
    if isinstance(warning_reasons, list):
        warnings.extend(str(reason) for reason in warning_reasons)
    return sorted(dict.fromkeys(blocking)), sorted(dict.fromkeys(warnings))


def _conflict_warnings(
    shadow_observations: dict[str, Any], shadow_quality: dict[str, Any]
) -> list[str]:
    warnings: list[str] = []
    for payload in (shadow_observations, shadow_quality):
        matrix = payload.get("conflict_matrix")
        if not isinstance(matrix, dict):
            continue
        for item in matrix.get("conflicting_tiles", []):
            if isinstance(item, dict) and isinstance(item.get("warning"), str):
                warnings.append(item["warning"])
    return sorted(dict.fromkeys(warnings))
