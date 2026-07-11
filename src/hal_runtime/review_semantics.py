"""Deterministic review failure categories and validation stages."""

from __future__ import annotations


def review_failure_category(
    blocking_reasons: list[str],
    *,
    decision_error: str | None = None,
    decision_missing_pending: bool = False,
    warnings_only: bool = False,
) -> str:
    reasons = set(blocking_reasons)
    if decision_error == "missing_review_decision" or decision_missing_pending:
        return "missing_review_decision"
    if decision_error == "invalid_review_decision_json" or "review_decision_invalid_json" in reasons:
        return "invalid_review_decision_json"
    priority = (
        ("wrong_approval_scope", "review_decision_approved_for_not_dry_run_only"),
        ("human_approval_missing", "review_decision_human_review_approved_false"),
        ("reviewer_identity_missing", "review_decision_reviewer_id_missing"),
        ("review_timestamp_missing", "review_decision_review_timestamp_missing"),
    )
    for category, reason in priority:
        if reason in reasons:
            return category
    if any("review_decision_acknowledgement_missing:" in reason for reason in reasons):
        return "acknowledgement_missing"
    if any(
        token in reason
        for reason in reasons
        for token in (
            "review_decision_safety_boundary",
            "review_decision_hardware_control_enabled",
            "review_decision_real_execution_allowed",
            "review_decision_certification_passed",
            "review_decision_simulation_only_not_true",
            "review_decision_claim_boundary",
        )
    ):
        return "decision_safety_boundary"
    if "candidate_review_package_blocked" in reasons:
        return "candidate_review_blocked"
    if any(reason.startswith("artifact_hash_mismatch:") for reason in reasons):
        return "artifact_integrity"
    if any(
        token in reason
        for reason in reasons
        for token in (
            "candidate_hardware_execution_enabled_true",
            "candidate_hardware_control_enabled_true",
            "candidate_voltage_policy_not_no_hardware_control",
            "candidate_runtime_loader_hint_not_simulation_only",
            "candidate_human_review_required_false",
            "candidate_claim_boundary",
        )
    ):
        return "candidate_safety_boundary"
    if any(reason.startswith("candidate_") for reason in reasons):
        return "candidate_invariant_failure"
    if warnings_only:
        return "warnings_only"
    return "none"


def review_validation_stage(
    blocking_reasons: list[str],
    *,
    decision_error: str | None = None,
    promotion: bool = False,
    completed: bool = False,
) -> str:
    reasons = set(blocking_reasons)
    if any(reason.startswith(("missing_review_artifact:", "invalid_review_json:", "missing_or_invalid_review_artifact:")) for reason in reasons):
        return "review_package_load"
    if decision_error == "missing_review_decision":
        return "review_decision_load"
    if decision_error == "invalid_review_decision_json":
        return "review_decision_json_parse"
    if any(reason.startswith("review_decision_") for reason in reasons):
        return "review_decision_validation"
    if "candidate_review_package_blocked" in reasons:
        return "candidate_review_validation"
    if any(reason.startswith("candidate_") for reason in reasons):
        return "candidate_safety_validation"
    if promotion and reasons:
        return "promotion_preflight"
    return "completed" if completed or not reasons else "candidate_review_validation"
