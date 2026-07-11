"""Validate Runtime plans and produce mock-only adapter simulation records."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .adapter_models import (
    AdapterSimulationOutcome,
    MockAdapterResult,
    PlanValidationResult,
)
from .adapter_registry import AdapterRegistry
from .adapter_report import build_adapter_report
from .event_log import write_events, write_json


REQUIRED_PLAN_FIELDS = (
    "runtime_version",
    "execution_mode",
    "hardware_control_enabled",
    "human_review_required",
    "claim_boundary",
    "actions",
    "blocked_actions",
    "plan_status",
    "plan_block_reasons",
)
EXECUTABLE_PLAN_STATUSES = {"planned", "planned_with_blocks"}
NONEXECUTABLE_PLAN_STATUSES = {
    "degraded_no_execution_plan",
    "blocked_by_safety_gate",
    "blocked_by_bundle_validation",
}
ALLOWED_PLAN_STATUSES = EXECUTABLE_PLAN_STATUSES | NONEXECUTABLE_PLAN_STATUSES


class PlanLoadError(ValueError):
    """Raised when a plan file cannot be decoded as a JSON object."""


def load_runtime_plan(path: str | Path) -> dict[str, Any]:
    plan_path = Path(path)
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PlanLoadError("plan_not_readable") from exc
    except json.JSONDecodeError as exc:
        raise PlanLoadError("invalid_json") from exc
    if not isinstance(plan, dict):
        raise PlanLoadError("plan_not_object")
    return plan


def validate_runtime_plan(plan: Mapping[str, Any]) -> PlanValidationResult:
    structural_reasons = [
        f"missing_required_field:{field}"
        for field in REQUIRED_PLAN_FIELDS
        if field not in plan
    ]
    if "runtime_version" in plan and not isinstance(plan["runtime_version"], str):
        structural_reasons.append("runtime_version_must_be_string")
    for field in ("actions", "blocked_actions", "plan_block_reasons"):
        if field in plan and not isinstance(plan[field], list):
            structural_reasons.append(f"{field}_must_be_list")
    if isinstance(plan.get("actions"), list) and not all(
        isinstance(action, dict) for action in plan["actions"]
    ):
        structural_reasons.append("actions_must_contain_objects")
    if "plan_status" in plan and (
        not isinstance(plan["plan_status"], str)
        or plan["plan_status"] not in ALLOWED_PLAN_STATUSES
    ):
        structural_reasons.append("plan_status_not_supported")

    safety_reasons: list[str] = []
    if "execution_mode" in plan and plan["execution_mode"] != "dry_run":
        safety_reasons.append("execution_mode_must_be_dry_run")
    if "hardware_control_enabled" in plan and plan["hardware_control_enabled"] is not False:
        safety_reasons.append("hardware_control_enabled_must_be_false")
    if "human_review_required" in plan and plan["human_review_required"] is not True:
        safety_reasons.append("human_review_required_must_be_true")
    if "claim_boundary" in plan and plan["claim_boundary"] != "simulation_only_not_certified":
        safety_reasons.append("claim_boundary_must_be_simulation_only_not_certified")

    return PlanValidationResult(
        structurally_valid=not structural_reasons,
        safety_boundary_passed=not structural_reasons and not safety_reasons,
        validation_reasons=tuple(structural_reasons),
        safety_failure_reasons=tuple(safety_reasons),
    )


def simulate_plan(
    plan: Mapping[str, Any], registry: AdapterRegistry | None = None
) -> AdapterSimulationOutcome:
    adapter_registry = registry or AdapterRegistry()
    available = len(adapter_registry.list_adapters())
    validation = validate_runtime_plan(plan)
    plan_status = plan.get("plan_status")
    status_value = plan_status if isinstance(plan_status, str) else "unknown"
    initial_events: list[dict[str, Any]] = [
        {"event_type": "plan_loaded", "status": "ok"}
    ]

    if not validation.structurally_valid:
        report = build_adapter_report(
            plan_loaded=True,
            plan_status=status_value,
            adapter_simulation_status="invalid_plan",
            adapter_execution_stage="plan_validation",
            available_adapters=available,
            source_plan=plan,
            validation_reasons=validation.validation_reasons,
        )
        return AdapterSimulationOutcome(
            report,
            tuple(initial_events)
            + (
                {
                    "event_type": "plan_validation_failed",
                    "status": "invalid_plan",
                    "reason": validation.validation_reasons[0],
                    "reasons": list(validation.validation_reasons),
                },
                {
                    "event_type": "adapter_simulation_blocked",
                    "status": "invalid_plan",
                },
            ),
        )

    if not validation.safety_boundary_passed:
        report = build_adapter_report(
            plan_loaded=True,
            plan_status=status_value,
            adapter_simulation_status="blocked_safety_boundary",
            adapter_execution_stage="adapter_safety_boundary",
            available_adapters=available,
            source_plan=plan,
            block_reasons=("safety_boundary_failed",),
            safety_failure_reasons=validation.safety_failure_reasons,
        )
        return AdapterSimulationOutcome(
            report,
            tuple(initial_events)
            + (
                {"event_type": "plan_validation_passed", "status": "ok"},
                {
                    "event_type": "adapter_safety_boundary_failed",
                    "status": "blocked",
                    "reason": validation.safety_failure_reasons[0],
                    "reasons": list(validation.safety_failure_reasons),
                },
                {
                    "event_type": "adapter_simulation_blocked",
                    "status": "blocked_safety_boundary",
                },
            ),
        )

    actions = plan["actions"]
    if status_value in NONEXECUTABLE_PLAN_STATUSES:
        report = build_adapter_report(
            plan_loaded=True,
            plan_status=status_value,
            adapter_simulation_status="skipped_plan_not_executable",
            adapter_execution_stage="plan_executable_check",
            available_adapters=available,
            source_plan=plan,
            skipped_actions=len(actions),
            block_reasons=(status_value,),
        )
        return AdapterSimulationOutcome(
            report,
            tuple(initial_events)
            + (
                {"event_type": "plan_validation_passed", "status": "ok"},
                {
                    "event_type": "adapter_safety_boundary_passed",
                    "status": "ok",
                },
                {
                    "event_type": "plan_executable_check_failed",
                    "status": "skipped_plan_not_executable",
                    "plan_status": status_value,
                },
                {
                    "event_type": "adapter_simulation_skipped",
                    "status": "skipped_plan_not_executable",
                },
            ),
        )

    events: list[dict[str, Any]] = initial_events + [
        {"event_type": "plan_validation_passed", "status": "ok"},
        {"event_type": "adapter_safety_boundary_passed", "status": "ok"},
        {
            "event_type": "plan_executable_check_passed",
            "status": "ok",
            "plan_status": status_value,
        },
        {
            "event_type": "adapter_simulation_started",
            "status": "ok",
            "plan_status": status_value,
        }
    ]
    results: list[MockAdapterResult] = []
    for action in actions:
        adapter, resolution_reason = adapter_registry.resolve(action)
        if adapter is None:
            simulation_status = (
                "blocked_unsupported_action"
                if resolution_reason == "unsupported_action_type"
                else "blocked_unsupported_role"
            )
            result = MockAdapterResult(
                adapter_id="unresolved_mock_adapter",
                action_id=str(action.get("action_id", "unknown")),
                action_type=str(action.get("action_type", "unknown")),
                workload_id=(
                    action.get("workload_id")
                    if isinstance(action.get("workload_id"), str)
                    else None
                ),
                simulation_status=simulation_status,
                simulation_reason=resolution_reason or "adapter_not_resolved",
            )
            results.append(result)
            events.append(
                {
                    "event_type": "adapter_resolution_failed",
                    "status": "blocked",
                    "action_id": result.action_id,
                    "reason": result.simulation_reason,
                }
            )
            events.append(
                {
                    "event_type": "action_blocked",
                    "status": simulation_status,
                    "action_id": result.action_id,
                }
            )
            continue

        events.append(
            {
                "event_type": "adapter_resolved",
                "status": "ok",
                "action_id": str(action.get("action_id", "unknown")),
                "adapter_id": adapter.info.adapter_id,
            }
        )
        result = adapter.simulate(action)
        results.append(result)
        events.append(
            {
                "event_type": (
                    "action_simulated"
                    if result.simulation_status == "simulated"
                    else "action_blocked"
                ),
                "status": result.simulation_status,
                "action_id": result.action_id,
                "adapter_id": result.adapter_id,
            }
        )

    blocked_count = sum(result.simulation_status != "simulated" for result in results)
    simulation_status = (
        "adapter_simulation_completed_with_blocks"
        if blocked_count
        else "adapter_simulation_passed"
    )
    report = build_adapter_report(
        plan_loaded=True,
        plan_status=status_value,
        adapter_simulation_status=simulation_status,
        adapter_execution_stage="adapter_simulation_completed",
        available_adapters=available,
        source_plan=plan,
        results=tuple(results),
    )
    events.append(
        {
            "event_type": "adapter_simulation_completed",
            "status": "completed_with_blocks" if blocked_count else "ok",
        }
    )
    return AdapterSimulationOutcome(report, tuple(events))


def simulate_plan_file(
    plan_path: str | Path, output_dir: str | Path
) -> AdapterSimulationOutcome:
    registry = AdapterRegistry()
    try:
        plan = load_runtime_plan(plan_path)
    except PlanLoadError as exc:
        report = build_adapter_report(
            plan_loaded=False,
            plan_status="unknown",
            adapter_simulation_status="invalid_plan",
            adapter_execution_stage="plan_load",
            available_adapters=len(registry.list_adapters()),
            validation_reasons=(str(exc),),
        )
        outcome = AdapterSimulationOutcome(
            report,
            (
                {
                    "event_type": "plan_load_failed",
                    "status": "invalid_plan",
                    "reason": str(exc),
                },
                {
                    "event_type": "adapter_simulation_blocked",
                    "status": "invalid_plan",
                },
            ),
        )
    else:
        outcome = simulate_plan(plan, registry)

    output_path = Path(output_dir)
    write_events(output_path / "adapter_trace.jsonl", outcome.trace_events)
    write_json(output_path / "adapter_report.json", outcome.report.to_dict())
    return outcome
