"""Construct audit reports for simulated rollback planning."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .adapter_report import build_source_plan_summary
from .failure_models import FailureInjectionResult, FailureScenario
from .rollback_models import RollbackPlan, RollbackReport


def build_rollback_report(
    source_plan: Mapping[str, Any] | None,
    scenario: FailureScenario,
    injection: FailureInjectionResult,
    rollback_plan: RollbackPlan,
    *,
    plan_loaded: bool = True,
    scenario_loaded: bool = True,
    status_override: str | None = None,
    failure_reasons_override: tuple[str, ...] | None = None,
) -> RollbackReport:
    if status_override:
        status = status_override
    elif rollback_plan.rollback_plan_status == "rollback_not_required":
        status = "rollback_not_required"
    elif rollback_plan.rollback_plan_status == "no_action_taken":
        status = "no_action_taken"
    elif rollback_plan.rollback_plan_status == "safe_stop_only":
        status = "safe_stop_planned"
    else:
        status = "rollback_plan_generated"
    rollback_reasons = tuple(
        dict.fromkeys(action.simulation_reason for action in rollback_plan.rollback_actions)
    )
    plan_payload = rollback_plan.to_dict()
    return RollbackReport(
        plan_loaded=plan_loaded,
        scenario_loaded=scenario_loaded,
        source_plan_summary=build_source_plan_summary(source_plan),
        scenario_summary=scenario.to_summary(),
        rollback_simulation_status=status,
        injected_failure_mode=scenario.failure_mode,
        injected_failure_action_id=injection.injected_failure_action_id,
        simulated_actions_before_failure=len(injection.simulated_action_ids),
        failed_actions=len(injection.failed_action_ids),
        skipped_actions=len(injection.skipped_action_ids),
        rollback_required=rollback_plan.rollback_required,
        safe_stop_required=rollback_plan.safe_stop_required,
        no_action_taken=rollback_plan.no_action_taken,
        rollback_actions_planned=len(rollback_plan.rollback_actions),
        simulated_revert_actions_planned=plan_payload[
            "simulated_revert_actions_planned"
        ],
        safe_stop_markers_planned=plan_payload["safe_stop_markers_planned"],
        skip_markers_planned=plan_payload["skip_markers_planned"],
        no_action_markers_planned=plan_payload["no_action_markers_planned"],
        rollback_strategy=rollback_plan.rollback_strategy,
        failure_reasons=(
            failure_reasons_override
            if failure_reasons_override is not None
            else injection.failure_reasons
        ),
        rollback_reasons=rollback_reasons,
    )
