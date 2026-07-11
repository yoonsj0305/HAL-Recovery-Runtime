"""Create inert rollback markers from simulated failure outcomes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .failure_models import FailureInjectionResult, FailureScenario
from .rollback_models import RollbackAction, RollbackPlan


NONEXECUTABLE_PLAN_STATUSES = {
    "blocked_by_safety_gate",
    "blocked_by_bundle_validation",
    "degraded_no_execution_plan",
}


def build_rollback_plan(
    source_plan: Mapping[str, Any],
    scenario: FailureScenario,
    injection: FailureInjectionResult,
) -> RollbackPlan:
    source_status = str(source_plan.get("plan_status", "unknown"))
    if source_status in NONEXECUTABLE_PLAN_STATUSES:
        return RollbackPlan(
            source_plan_status=source_status,
            scenario_id=scenario.scenario_id,
            failure_mode=scenario.failure_mode,
            rollback_required=False,
            safe_stop_required=False,
            no_action_taken=True,
            rollback_plan_status="no_action_taken",
            rollback_strategy="no_action_taken",
        )
    if scenario.failure_mode == "none" and not injection.failed_action_ids:
        return RollbackPlan(
            source_plan_status=source_status,
            scenario_id=scenario.scenario_id,
            failure_mode=scenario.failure_mode,
            rollback_required=False,
            safe_stop_required=False,
            no_action_taken=False,
            rollback_plan_status="rollback_not_required",
            rollback_strategy="none",
        )
    if scenario.failure_mode == "forced_safety_boundary_failure":
        return RollbackPlan(
            source_plan_status=source_status,
            scenario_id=scenario.scenario_id,
            failure_mode=scenario.failure_mode,
            rollback_required=False,
            safe_stop_required=False,
            no_action_taken=True,
            rollback_plan_status="no_action_taken",
            rollback_strategy="no_action_taken",
        )

    actions: list[RollbackAction] = []
    safe_stop_mode = scenario.failure_mode in {
        "adapter_unavailable",
        "action_timeout",
        "unsupported_role_after_injection",
    }
    if safe_stop_mode and injection.simulated_action_ids:
        for index, action_id in enumerate(reversed(injection.simulated_action_ids), start=1):
            actions.append(
                RollbackAction(
                    f"RB_{index:03d}",
                    "simulated_revert",
                    action_id,
                    "planned",
                    "source_action_was_simulated_before_injected_failure",
                )
            )
        actions.append(
            RollbackAction(
                f"RB_{len(actions) + 1:03d}",
                "safe_stop_marker",
                injection.injected_failure_action_id,
                "planned",
                "simulated_failure_requires_safe_stop",
            )
        )
        return RollbackPlan(
            source_plan_status=source_status,
            scenario_id=scenario.scenario_id,
            failure_mode=scenario.failure_mode,
            rollback_required=True,
            safe_stop_required=True,
            no_action_taken=False,
            rollback_plan_status="planned_simulation_with_safe_stop",
            rollback_strategy="simulated_revert_completed_actions_with_safe_stop",
            rollback_actions=tuple(actions),
        )
    if safe_stop_mode:
        actions.append(
            RollbackAction(
                "RB_001",
                "safe_stop_marker",
                injection.injected_failure_action_id,
                "planned",
                "simulated_failure_requires_safe_stop",
            )
        )
        return RollbackPlan(
            source_plan_status=source_status,
            scenario_id=scenario.scenario_id,
            failure_mode=scenario.failure_mode,
            rollback_required=False,
            safe_stop_required=True,
            no_action_taken=False,
            rollback_plan_status="safe_stop_only",
            rollback_strategy="safe_stop",
            rollback_actions=tuple(actions),
        )
    if injection.rollback_strategy in {
        "simulated_revert_completed_actions",
        "rollback_to_pre_simulation_state",
    } and injection.simulated_action_ids:
        for index, action_id in enumerate(reversed(injection.simulated_action_ids), start=1):
            actions.append(
                RollbackAction(
                    f"RB_{index:03d}",
                    "simulated_revert",
                    action_id,
                    "planned",
                    "source_action_was_simulated_before_injected_failure",
                )
            )
        return RollbackPlan(
            source_plan_status=source_status,
            scenario_id=scenario.scenario_id,
            failure_mode=scenario.failure_mode,
            rollback_required=True,
            safe_stop_required=False,
            no_action_taken=False,
            rollback_plan_status="planned_simulation_only",
            rollback_strategy=injection.rollback_strategy,
            rollback_actions=tuple(actions),
        )
    return RollbackPlan(
        source_plan_status=source_status,
        scenario_id=scenario.scenario_id,
        failure_mode=scenario.failure_mode,
        rollback_required=False,
        safe_stop_required=False,
        no_action_taken=True,
        rollback_plan_status="no_action_taken",
        rollback_strategy="no_action_taken",
    )
