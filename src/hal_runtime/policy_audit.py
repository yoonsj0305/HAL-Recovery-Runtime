"""Deterministic, bounded audit helpers for policy simulation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


POLICY_PRECEDENCE_ORDER = (
    "invalid_input",
    "policy_config_safety_boundary",
    "runtime_plan_safety_boundary",
    "adapter_safety_boundary",
    "rollback_no_action_taken",
    "rollback_required_with_safe_stop",
    "rollback_required",
    "safe_stop_required",
    "source_plan_not_executable",
    "adapter_blocks",
    "degraded_plan",
    "conservative_human_review",
    "dry_run_allowed_with_warnings",
)

RULE_EFFECTS = {
    "invalid_input": "block",
    "policy_config_safety_boundary": "block",
    "runtime_plan_safety_boundary": "block",
    "adapter_safety_boundary": "block",
    "rollback_no_action_taken": "no_action",
    "rollback_required_with_safe_stop": "rollback_then_safe_stop",
    "rollback_required": "rollback",
    "safe_stop_required": "safe_stop",
    "source_plan_not_executable": "no_action",
    "adapter_blocks": "human_review",
    "degraded_plan": "human_review",
    "conservative_human_review": "human_review",
    "dry_run_allowed_with_warnings": "warning",
}


def build_rule_results(matches: Mapping[str, str]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "rule": rule,
            "matched": rule in matches,
            "effect": RULE_EFFECTS[rule],
            "reason": matches.get(rule),
        }
        for rule in POLICY_PRECEDENCE_ORDER
    )


def first_matched_rule(rule_results: tuple[dict[str, Any], ...]) -> str:
    for result in rule_results:
        if result["matched"]:
            return str(result["rule"])
    return "conservative_human_review"


def build_policy_input_summary(
    plan: Mapping[str, Any] | None,
    adapter_report: Mapping[str, Any] | None,
    rollback_report: Mapping[str, Any] | None,
    *,
    policy_config_present: bool,
    policy_mode: str,
) -> dict[str, Any]:
    plan_reasons = plan.get("plan_block_reasons") if plan else None
    return {
        "runtime_plan_present": plan is not None,
        "adapter_report_present": adapter_report is not None,
        "rollback_report_present": rollback_report is not None,
        "policy_config_present": policy_config_present,
        "plan_status": plan.get("plan_status") if plan else None,
        "adapter_simulation_status": (
            adapter_report.get("adapter_simulation_status")
            if adapter_report is not None
            else None
        ),
        "rollback_simulation_status": (
            rollback_report.get("rollback_simulation_status")
            if rollback_report is not None
            else None
        ),
        "rollback_required": bool(
            rollback_report and rollback_report.get("rollback_required") is True
        ),
        "safe_stop_required": bool(
            rollback_report and rollback_report.get("safe_stop_required") is True
        ),
        "no_action_taken": bool(
            rollback_report and rollback_report.get("no_action_taken") is True
        ),
        "adapter_blocked_actions": (
            adapter_report.get("blocked_actions", 0)
            if adapter_report is not None
            else 0
        ),
        "plan_block_reasons_count": (
            len(plan_reasons) if isinstance(plan_reasons, list) else 0
        ),
        "policy_config_mode": policy_mode,
    }


def build_conflict_reasons(
    plan: Mapping[str, Any],
    adapter_report: Mapping[str, Any] | None,
    rollback_report: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    rollback = bool(rollback_report and rollback_report.get("rollback_required") is True)
    safe_stop = bool(rollback_report and rollback_report.get("safe_stop_required") is True)
    no_action = bool(rollback_report and rollback_report.get("no_action_taken") is True)
    adapter_blocks = bool(adapter_report and adapter_report.get("blocked_actions", 0) > 0)
    degraded = plan.get("plan_status") == "degraded_no_execution_plan" or bool(
        plan.get("degraded_bundle_mode")
    )
    conflicts: list[str] = []
    if rollback and safe_stop:
        conflicts.append("rollback_and_safe_stop_both_required")
    if adapter_blocks and rollback:
        conflicts.append("adapter_blocks_present_but_rollback_has_higher_precedence")
    if degraded and adapter_blocks:
        conflicts.append("multiple_review_reasons:degraded_plan,adapter_blocks")
    if no_action and rollback:
        conflicts.append("no_action_takes_precedence_over_rollback")
    return tuple(conflicts)


def build_warning_inputs(
    plan: Mapping[str, Any],
    adapter_report: Mapping[str, Any] | None,
    rollback_report: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    inputs: list[str] = []
    if adapter_report and adapter_report.get("blocked_actions", 0) > 0:
        inputs.extend(
            ("adapter_report.blocked_actions", "adapter_report.adapter_block_reasons")
        )
    if plan.get("plan_status") == "degraded_no_execution_plan":
        inputs.append("runtime_plan.degraded_no_execution_plan")
    if bool(plan.get("degraded_bundle_mode")):
        inputs.append("bundle.degraded_missing_artifacts")
    if rollback_report and rollback_report.get("safe_stop_required") is True:
        inputs.append("rollback_report.safe_stop_required")
    if rollback_report and rollback_report.get("rollback_required") is True:
        inputs.append("rollback_report.rollback_required")
    return tuple(dict.fromkeys(inputs))


def build_decision_path(
    *,
    plan_loaded: bool,
    policy_config_present: bool,
    policy_config_loaded: bool,
    matched_rule: str,
    selected_policy: str,
    policy_status: str,
    blocking_reason: str | None = None,
    blocking_step: str = "policy_safety_boundary_failed",
) -> tuple[dict[str, Any], ...]:
    path: list[dict[str, Any]] = [
        {
            "step": "runtime_plan_loaded",
            "status": "ok" if plan_loaded else "failed",
            "reason": "plan_loaded" if plan_loaded else "plan_not_loaded",
        },
        {
            "step": "policy_config_loaded",
            "status": (
                "ok" if policy_config_present and policy_config_loaded
                else "failed" if policy_config_present
                else "default"
            ),
            "reason": (
                "policy_config_loaded" if policy_config_present and policy_config_loaded
                else "policy_config_not_loaded" if policy_config_present
                else "no_policy_config_provided"
            ),
        },
    ]
    if blocking_reason:
        path.append(
            {
                "step": blocking_step,
                "status": "blocked",
                "reason": blocking_reason,
            }
        )
    path.extend(
        (
            {
                "step": "policy_precedence_evaluated",
                "status": "blocked" if policy_status.startswith("blocked_") or policy_status == "invalid_policy_input" else "matched",
                "reason": f"first_matched_rule:{matched_rule}",
                "matched_rule": matched_rule,
                "selected_policy": selected_policy,
                "policy_status": policy_status,
            },
            {
                "step": "policy_decision_selected",
                "status": "ok" if not policy_status.startswith("blocked_") and policy_status != "invalid_policy_input" else "blocked",
                "reason": f"selected_by:{matched_rule}",
                "matched_rule": matched_rule,
                "selected_policy": selected_policy,
                "policy_status": policy_status,
            },
        )
    )
    return tuple(path)
