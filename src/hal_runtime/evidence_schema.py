"""Fixed artifact schema for simulation-only evidence bundles."""

from __future__ import annotations

from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .models import RUNTIME_VERSION


EVIDENCE_BUNDLE_VERSION = RUNTIME_VERSION
EVIDENCE_VALIDATION_SEMANTICS_VERSION = RUNTIME_VERSION
MAX_ARTIFACT_SIZE_BYTES = 5 * 1024 * 1024

EVIDENCE_VALIDATION_PRIORITY_ORDER = (
    "blocked_safety_boundary",
    "invalid_artifact_json",
    "invalid_missing_required_artifacts",
    "invalid_missing_manifest_entries",
    "invalid_missing_copied_artifacts",
    "invalid_hash_mismatch",
    "invalid_profile_id_mismatch",
    "invalid_policy_decision_mismatch",
    "invalid_policy_runtime_inconsistency",
    "valid_with_warnings",
    "valid_evidence_bundle",
)

FAILURE_CATEGORIES = {
    "valid_evidence_bundle": "none",
    "valid_with_warnings": "warnings_only",
    "invalid_missing_required_artifacts": "missing_required_artifact",
    "invalid_artifact_json": "invalid_json",
    "invalid_hash_mismatch": "hash_integrity",
    "invalid_missing_manifest_entries": "manifest_integrity",
    "invalid_missing_copied_artifacts": "copied_artifact_integrity",
    "invalid_profile_id_mismatch": "profile_consistency",
    "invalid_policy_decision_mismatch": "policy_consistency",
    "invalid_policy_runtime_inconsistency": "runtime_policy_consistency",
    "blocked_safety_boundary": "safety_boundary",
}

VALIDATION_STAGES = {
    "valid_evidence_bundle": "completed",
    "valid_with_warnings": "completed",
    "invalid_missing_required_artifacts": "artifact_discovery",
    "invalid_artifact_json": "json_parsing",
    "invalid_hash_mismatch": "copied_artifact_validation",
    "invalid_missing_manifest_entries": "manifest_validation",
    "invalid_missing_copied_artifacts": "copied_artifact_validation",
    "invalid_profile_id_mismatch": "profile_consistency_check",
    "invalid_policy_decision_mismatch": "policy_consistency_check",
    "invalid_policy_runtime_inconsistency": "runtime_policy_consistency_check",
    "blocked_safety_boundary": "safety_boundary_check",
}

VALIDATION_MATRIX_KEYS = (
    "required_artifacts",
    "json_validity",
    "hash_integrity",
    "manifest_integrity",
    "copied_artifacts",
    "safety_boundary",
    "profile_consistency",
    "policy_consistency",
    "runtime_policy_consistency",
    "warnings",
)


def build_validation_matrix(
    failures: dict[str, list[str]], warnings: list[str] | tuple[str, ...]
) -> dict[str, dict[str, Any]]:
    matrix: dict[str, dict[str, Any]] = {}
    for key in VALIDATION_MATRIX_KEYS:
        reasons = list(warnings) if key == "warnings" else list(failures.get(key, []))
        failed = key != "warnings" and bool(reasons)
        matrix[key] = {
            "passed": not failed,
            "status": (
                "warnings_present"
                if key == "warnings" and reasons
                else "failed" if failed else "ok"
            ),
            "reasons": reasons,
        }
    return matrix

ARTIFACT_TYPES = {
    "recovery_profile.json": "recovery_profile",
    "functional_passport.json": "functional_passport",
    "runtime_plan.json": "runtime_plan",
    "runtime_report.json": "runtime_report",
    "runtime_events.jsonl": "runtime_events",
    "bundle_validation_report.json": "bundle_validation_report",
    "solver_report.json": "solver_report",
    "artifact_validation_report.json": "artifact_validation_report",
    "comparison_report.json": "comparison_report",
    "adapter_report.json": "adapter_report",
    "adapter_trace.jsonl": "adapter_trace",
    "adapter_registry.json": "adapter_registry",
    "failure_trace.jsonl": "failure_trace",
    "rollback_plan.json": "rollback_plan",
    "rollback_report.json": "rollback_report",
    "failure_modes.json": "failure_modes",
    "policy_decision.json": "policy_decision",
    "policy_report.json": "policy_report",
    "policy_trace.jsonl": "policy_trace",
    "policy_modes.json": "policy_modes",
}

REQUIRED_ARTIFACTS = (
    "runtime_plan.json",
    "runtime_report.json",
    "policy_report.json",
    "policy_decision.json",
)
OPTIONAL_ARTIFACTS = tuple(
    name for name in ARTIFACT_TYPES if name not in REQUIRED_ARTIFACTS
)


def expected_optional_artifacts(present: set[str]) -> tuple[str, ...]:
    expected: list[str] = []
    if "runtime_report.json" in present:
        expected.append("runtime_events.jsonl")
    if "adapter_report.json" in present:
        expected.append("adapter_trace.jsonl")
    if "rollback_report.json" in present:
        expected.extend(("rollback_plan.json", "failure_trace.jsonl"))
    if "policy_report.json" in present:
        expected.append("policy_trace.jsonl")
    return tuple(name for name in expected if name not in present)


def evidence_schema_document() -> dict[str, Any]:
    return {
        "runtime_version": RUNTIME_VERSION,
        "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "required_artifacts": list(REQUIRED_ARTIFACTS),
        "recognized_optional_artifacts": list(OPTIONAL_ARTIFACTS),
        "known_limitations": [
            "schema_lists_expected_artifacts_only",
            "not_certification",
        ],
    }
