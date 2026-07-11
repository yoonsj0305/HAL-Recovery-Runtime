"""Construct a summary of an inert dry-run."""

from __future__ import annotations

from .models import RuntimePlan, RuntimeReport, SafetyGateResult


def build_runtime_report(
    plan: RuntimePlan, gate_result: SafetyGateResult
) -> RuntimeReport:
    if not gate_result.passed:
        status = "blocked_by_safety_gate"
    elif gate_result.degraded_mode:
        status = "degraded_no_execution_plan"
    elif plan.blocked_actions:
        status = "dry_run_completed_with_blocks"
    else:
        status = "dry_run_passed"

    if not gate_result.passed:
        execution_gate_stage = "single_file_safety_gate"
    elif gate_result.degraded_mode:
        execution_gate_stage = "plan_builder"
    else:
        execution_gate_stage = "dry_run_completed"

    return RuntimeReport(
        profile_loaded=True,
        safety_gate_passed=gate_result.passed,
        planned_actions=len(plan.actions),
        blocked_actions=len(plan.blocked_actions),
        degraded_mode_entered=gate_result.degraded_mode,
        runtime_status=status,
        hardware_control_enabled=plan.hardware_control_enabled,
        human_review_required=plan.human_review_required,
        claim_boundary=plan.claim_boundary,
        safety_gate_evaluated=True,
        bundle_gate_evaluated=False,
        execution_gate_stage=execution_gate_stage,
        safety_failure_reasons=gate_result.failure_reasons,
        degraded_mode_reasons=(
            ("preferred_routes_missing",) if gate_result.degraded_mode else ()
        ),
        blocked_action_details=tuple(action.to_dict() for action in plan.blocked_actions),
    )
