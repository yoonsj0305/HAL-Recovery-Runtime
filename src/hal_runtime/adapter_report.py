"""Helpers for constructing adapter-layer audit reports."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .adapter_models import (
    AdapterResultSummary,
    AdapterSimulationReport,
    MockAdapterResult,
    SourcePlanSummary,
)


def build_adapter_report(
    *,
    plan_loaded: bool,
    plan_status: str,
    adapter_simulation_status: str,
    adapter_execution_stage: str,
    available_adapters: int,
    source_plan: Mapping[str, Any] | None = None,
    results: tuple[MockAdapterResult, ...] = (),
    skipped_actions: int = 0,
    block_reasons: tuple[str, ...] = (),
    safety_failure_reasons: tuple[str, ...] = (),
    validation_reasons: tuple[str, ...] = (),
) -> AdapterSimulationReport:
    simulated = sum(result.simulation_status == "simulated" for result in results)
    blocked = len(results) - simulated
    derived_block_reasons = tuple(
        _result_block_reason(result)
        for result in results
        if result.simulation_status != "simulated"
    )
    return AdapterSimulationReport(
        plan_loaded=plan_loaded,
        plan_status=plan_status,
        adapter_simulation_status=adapter_simulation_status,
        available_adapters=available_adapters,
        simulated_actions=simulated,
        blocked_actions=blocked,
        skipped_actions=skipped_actions,
        adapter_execution_stage=adapter_execution_stage,
        source_plan_summary=build_source_plan_summary(source_plan),
        adapter_result_summary=_result_summary(results, skipped_actions),
        adapter_block_reasons=tuple(
            dict.fromkeys(reason for reason in block_reasons + derived_block_reasons if reason)
        ),
        adapter_safety_failure_reasons=safety_failure_reasons,
        adapter_validation_reasons=validation_reasons,
        adapter_results=results,
    )


def build_source_plan_summary(plan: Mapping[str, Any] | None) -> SourcePlanSummary:
    if plan is None:
        return SourcePlanSummary(None, None, None, None, 0, 0)
    actions = plan.get("actions")
    blocked_actions = plan.get("blocked_actions")
    reasons = plan.get("plan_block_reasons")
    return SourcePlanSummary(
        runtime_version=(
            plan.get("runtime_version")
            if isinstance(plan.get("runtime_version"), str)
            else None
        ),
        profile_id=(
            plan.get("profile_id") if isinstance(plan.get("profile_id"), str) else None
        ),
        execution_mode=(
            plan.get("execution_mode")
            if isinstance(plan.get("execution_mode"), str)
            else None
        ),
        plan_status=(
            plan.get("plan_status") if isinstance(plan.get("plan_status"), str) else None
        ),
        planned_action_count=len(actions) if isinstance(actions, list) else 0,
        blocked_action_count=(
            len(blocked_actions) if isinstance(blocked_actions, list) else 0
        ),
        plan_block_reasons=(
            tuple(reason for reason in reasons if isinstance(reason, str))
            if isinstance(reasons, list)
            else ()
        ),
    )


def _result_summary(
    results: tuple[MockAdapterResult, ...], skipped_actions: int
) -> AdapterResultSummary:
    counts = {
        "simulated": 0,
        "blocked_unsupported_action": 0,
        "blocked_unsupported_role": 0,
        "blocked_safety_boundary": 0,
        "skipped_plan_not_executable": skipped_actions,
    }
    for result in results:
        if result.simulation_status in counts:
            counts[result.simulation_status] += 1
    return AdapterResultSummary(**counts)


def _result_block_reason(result: MockAdapterResult) -> str:
    if result.simulation_status == "blocked_unsupported_action":
        return "unsupported_action_type"
    if result.simulation_status == "blocked_unsupported_role":
        return result.simulation_reason
    if result.simulation_status == "blocked_safety_boundary":
        return "safety_boundary_failed"
    return ""
