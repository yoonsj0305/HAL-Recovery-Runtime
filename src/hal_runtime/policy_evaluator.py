"""Pure decision logic with deterministic policy precedence and audit evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .policy_audit import (
    build_conflict_reasons,
    build_decision_path,
    build_rule_results,
    build_warning_inputs,
    first_matched_rule,
)
from .policy_models import PolicyConfig, PolicyDecision


NONEXECUTABLE_PLAN_STATUSES = {
    "blocked_by_safety_gate",
    "blocked_by_bundle_validation",
}


def evaluate_policy(
    plan: Mapping[str, Any],
    config: PolicyConfig,
    adapter_report: Mapping[str, Any] | None = None,
    rollback_report: Mapping[str, Any] | None = None,
    *,
    policy_config_present: bool = False,
) -> PolicyDecision:
    plan_status = str(plan.get("plan_status", "unknown"))
    adapter_safety = bool(
        adapter_report
        and adapter_report.get("adapter_simulation_status") == "blocked_safety_boundary"
    )
    rollback_boundary = bool(
        rollback_report
        and str(rollback_report.get("rollback_simulation_status", "")).startswith(
            "blocked_"
        )
    )
    no_action = bool(
        rollback_report and rollback_report.get("no_action_taken") is True
    )
    rollback = bool(
        rollback_report and rollback_report.get("rollback_required") is True
    )
    safe_stop = bool(
        rollback_report and rollback_report.get("safe_stop_required") is True
    )
    adapter_blocks = bool(
        adapter_report and adapter_report.get("blocked_actions", 0) > 0
    )
    degraded = plan_status == "degraded_no_execution_plan" or bool(
        plan.get("degraded_bundle_mode")
    )
    source_not_executable = plan_status in NONEXECUTABLE_PLAN_STATUSES
    has_plan_warnings = plan_status == "planned_with_blocks" or bool(
        plan.get("plan_block_reasons")
    )

    matches: dict[str, str] = {"conservative_human_review": "conservative_default_requires_human_review"}
    if adapter_safety or rollback_boundary:
        matches["adapter_safety_boundary"] = (
            "adapter_safety_boundary_failed"
            if adapter_safety
            else "rollback_safety_boundary_failed"
        )
    if no_action:
        matches["rollback_no_action_taken"] = "rollback_report_no_action_taken"
    if rollback and safe_stop:
        matches["rollback_required_with_safe_stop"] = (
            "rollback_and_safe_stop_required"
        )
    if rollback:
        matches["rollback_required"] = "rollback_required"
    if safe_stop:
        matches["safe_stop_required"] = "safe_stop_required"
    if source_not_executable:
        matches["source_plan_not_executable"] = (
            f"source_plan_not_executable:{plan_status}"
        )
    if adapter_blocks:
        matches["adapter_blocks"] = "adapter_blocks_present"
    if degraded:
        matches["degraded_plan"] = "degraded_mode_requires_human_review"
    if has_plan_warnings:
        matches["dry_run_allowed_with_warnings"] = "plan_warnings_present"

    rule_results = build_rule_results(matches)
    matched_rule = first_matched_rule(rule_results)
    conflicts = build_conflict_reasons(plan, adapter_report, rollback_report)
    warning_inputs = build_warning_inputs(plan, adapter_report, rollback_report)

    selected, status, reasons, blocked, blocking_inputs = _outcome_for_rule(
        matched_rule,
        plan_status,
        config,
        adapter_report,
        rollback_report,
    )
    if matched_rule == "rollback_required" and selected == "no_action_taken":
        rule_results = tuple(
            {**result, "effect": "no_action"}
            if result["rule"] == matched_rule
            else result
            for result in rule_results
        )
    warning_reasons = _warning_reasons(
        plan, adapter_report, rollback_report, warning_inputs
    )
    if config.policy_mode == "no_retry_v0_5_0" and matched_rule == "conservative_human_review":
        reasons = ("retry_forbidden_in_v0_5_0",) + reasons
    path = build_decision_path(
        plan_loaded=True,
        policy_config_present=policy_config_present,
        policy_config_loaded=True,
        matched_rule=matched_rule,
        selected_policy=selected,
        policy_status=status,
        blocking_reason=blocked[0] if blocked else None,
    )
    return PolicyDecision(
        policy_config_id=config.policy_config_id,
        policy_mode=config.policy_mode,
        selected_policy=selected,
        policy_status=status,
        policy_reasons=tuple(dict.fromkeys(reasons)),
        blocked_reasons=tuple(dict.fromkeys(blocked)),
        warning_reasons=warning_reasons,
        policy_decision_path=path,
        policy_conflict_reasons=conflicts,
        policy_blocking_inputs=blocking_inputs,
        policy_warning_inputs=warning_inputs,
        policy_rule_results=rule_results,
    )


def _outcome_for_rule(
    rule: str,
    plan_status: str,
    config: PolicyConfig,
    adapter_report: Mapping[str, Any] | None,
    rollback_report: Mapping[str, Any] | None,
) -> tuple[str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    if rule == "adapter_safety_boundary":
        reasons = _string_tuple(
            adapter_report.get("adapter_safety_failure_reasons")
            if adapter_report
            else rollback_report.get("failure_reasons") if rollback_report else None
        ) or ("policy_input_safety_boundary_failed",)
        selected = (
            "no_action_taken"
            if config.policy_mode == "no_action_on_boundary_failure"
            else "blocked_by_safety_boundary"
        )
        field = (
            "adapter_report.adapter_simulation_status"
            if adapter_report
            else "rollback_report.rollback_simulation_status"
        )
        return selected, "blocked_by_safety_boundary", (), reasons, (field,)
    if rule == "rollback_no_action_taken":
        return (
            "no_action_taken",
            "policy_no_action_taken",
            ("rollback_report_no_action_taken",),
            (),
            ("rollback_report.no_action_taken",),
        )
    if rule == "rollback_required_with_safe_stop":
        return (
            "rollback_then_safe_stop_simulation_only",
            "policy_rollback_required",
            ("rollback_required", "safe_stop_required"),
            (),
            (),
        )
    if rule == "rollback_required":
        prior = int(rollback_report.get("simulated_revert_actions_planned", 0)) if rollback_report else 0
        if config.policy_mode == "rollback_if_prior_actions" and prior <= 0:
            return (
                "no_action_taken",
                "policy_no_action_taken",
                ("rollback_requested_without_prior_simulated_actions",),
                (),
                ("rollback_report.rollback_required",),
            )
        return "rollback_simulation_only", "policy_rollback_required", ("rollback_required",), (), ()
    if rule == "safe_stop_required":
        return "safe_stop_simulation_only", "policy_safe_stop_required", ("safe_stop_required",), (), ()
    if rule == "source_plan_not_executable":
        return (
            "no_action_taken",
            "policy_no_action_taken",
            (f"source_plan_not_executable:{plan_status}",),
            (),
            ("runtime_plan.plan_status",),
        )
    if rule == "adapter_blocks":
        return "human_review_required", "policy_requires_human_review", ("adapter_blocks_present",), (), ()
    if rule == "degraded_plan":
        return "human_review_required", "policy_requires_human_review", ("degraded_mode_requires_human_review",), (), ()
    return (
        "human_review_required",
        "policy_requires_human_review",
        ("conservative_default_requires_human_review",),
        (),
        (),
    )


def _warning_reasons(
    plan: Mapping[str, Any],
    adapter_report: Mapping[str, Any] | None,
    rollback_report: Mapping[str, Any] | None,
    warning_inputs: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if "adapter_report.blocked_actions" in warning_inputs:
        reasons.append("adapter_blocks_present")
        reasons.extend(
            _string_tuple(adapter_report.get("adapter_block_reasons"))
            if adapter_report
            else ()
        )
    if "runtime_plan.degraded_no_execution_plan" in warning_inputs:
        reasons.append("degraded_mode_requires_human_review")
    if "bundle.degraded_missing_artifacts" in warning_inputs:
        reasons.append("degraded_bundle_mode")
    if rollback_report and rollback_report.get("rollback_required") is True:
        reasons.append("rollback_required")
    if rollback_report and rollback_report.get("safe_stop_required") is True:
        reasons.append("safe_stop_required")
    return tuple(dict.fromkeys(reasons))


def _string_tuple(value: Any) -> tuple[str, ...]:
    return (
        tuple(item for item in value if isinstance(item, str))
        if isinstance(value, list)
        else ()
    )
