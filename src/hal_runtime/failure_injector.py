"""Apply controlled failures to mock-simulatable action records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .adapter_registry import AdapterRegistry
from .failure_models import FailureInjectionResult, FailureScenario


def inject_failure(
    plan: Mapping[str, Any],
    scenario: FailureScenario,
    registry: AdapterRegistry | None = None,
) -> FailureInjectionResult:
    actions = plan.get("actions", [])
    adapter_registry = registry or AdapterRegistry()
    if scenario.failure_mode == "forced_safety_boundary_failure":
        ids = tuple(_action_id(action) for action in actions)
        return FailureInjectionResult(
            (),
            (),
            ids,
            ("forced_safety_boundary_failure",),
            "no_action_taken",
            None,
            tuple((action_id, "skipped") for action_id in ids),
        )

    if scenario.failure_mode == "none":
        return _simulate_without_injection(actions, adapter_registry)

    target_index = _target_index(actions, scenario)
    simulated: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []
    outcomes: list[tuple[str, str]] = []
    failure_action_id: str | None = None
    for index, action in enumerate(actions):
        action_id = _action_id(action)
        if index < target_index:
            adapter, _ = adapter_registry.resolve(action)
            if adapter is not None and adapter.simulate(action).simulation_status == "simulated":
                simulated.append(action_id)
                outcomes.append((action_id, "simulated"))
                continue
            failed.append(action_id)
            outcomes.append((action_id, "failed"))
            failure_action_id = action_id
            target_index = index
            continue
        if index == target_index:
            failed.append(action_id)
            outcomes.append((action_id, "failed"))
            failure_action_id = action_id
        else:
            skipped.append(action_id)
            outcomes.append((action_id, "skipped"))

    reasons = [f"{scenario.failure_mode}:{failure_action_id or 'no_target'}"]
    if scenario.failure_mode == "action_timeout":
        reasons.append("retry_not_allowed_in_v0_4_1")
    return FailureInjectionResult(
        tuple(simulated),
        tuple(failed),
        tuple(skipped),
        tuple(reasons),
        _strategy(scenario.failure_mode),
        failure_action_id,
        tuple(outcomes),
    )


def _simulate_without_injection(
    actions: list[dict[str, Any]], registry: AdapterRegistry
) -> FailureInjectionResult:
    simulated: list[str] = []
    failed: list[str] = []
    outcomes: list[tuple[str, str]] = []
    reasons: list[str] = []
    for action in actions:
        action_id = _action_id(action)
        adapter, resolution_reason = registry.resolve(action)
        if adapter is None or adapter.simulate(action).simulation_status != "simulated":
            failed.append(action_id)
            outcomes.append((action_id, "failed"))
            reasons.append(f"mock_adapter_rejected:{resolution_reason or action_id}")
        else:
            simulated.append(action_id)
            outcomes.append((action_id, "simulated"))
    return FailureInjectionResult(
        tuple(simulated),
        tuple(failed),
        (),
        tuple(reasons),
        "none" if not failed else "safe_stop",
        failed[0] if failed else None,
        tuple(outcomes),
    )


def _target_index(actions: list[dict[str, Any]], scenario: FailureScenario) -> int:
    if scenario.target_action_id:
        for index, action in enumerate(actions):
            if action.get("action_id") == scenario.target_action_id:
                return index
    if scenario.failure_mode == "partial_plan_failure" and len(actions) > 1:
        return 1
    return 0


def _action_id(action: Mapping[str, Any]) -> str:
    return str(action.get("action_id", "unknown"))


def _strategy(mode: str) -> str:
    return {
        "adapter_unavailable": "safe_stop",
        "action_timeout": "safe_stop",
        "route_unavailable": "rollback_to_pre_simulation_state",
        "unsupported_role_after_injection": "safe_stop",
        "partial_plan_failure": "simulated_revert_completed_actions",
    }[mode]
