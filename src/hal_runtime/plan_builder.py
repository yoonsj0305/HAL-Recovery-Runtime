"""Translate compiler assignments into inert dry-run plan records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import RuntimeAction, RuntimePlan, SafetyGateResult


SUPPORTED_ACTION = "assign_workload"
REQUIRED_ROUTE_STATUS = "candidate_simulated"


def _string_tuple(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return tuple(value)


def build_runtime_plan(
    profile: Mapping[str, Any], gate_result: SafetyGateResult
) -> RuntimePlan:
    """Build records only; no external side effects are possible here."""
    base = {
        "profile_id": str(profile.get("profile_id", "unknown")),
        "hardware_control_enabled": profile.get("hardware_control_enabled") is not False,
        "human_review_required": profile.get("human_review_required") is True,
        "claim_boundary": profile.get("claim_boundary")
        if isinstance(profile.get("claim_boundary"), str)
        else None,
    }
    if not gate_result.passed:
        return RuntimePlan(
            **base,
            plan_status="blocked_by_safety_gate",
            plan_block_reasons=gate_result.failure_reasons,
        )
    if gate_result.degraded_mode:
        return RuntimePlan(
            **base,
            plan_status="degraded_no_execution_plan",
            plan_block_reasons=("preferred_routes_missing",),
        )

    actions: list[RuntimeAction] = []
    blocked: list[RuntimeAction] = []
    next_id = 1

    routes_by_workload: dict[str, list[Mapping[str, Any]]] = {}
    for route in profile.get("preferred_routes", []):
        if isinstance(route, Mapping) and isinstance(route.get("workload_id"), str):
            routes_by_workload.setdefault(route["workload_id"], []).append(route)

    allowed_roles = set(profile.get("allowed_roles", []))
    blocked_roles = set(profile.get("blocked_roles", []))

    for workload in profile.get("assigned_workloads", []):
        action_id = f"ACT_{next_id:03d}"
        next_id += 1
        if not isinstance(workload, Mapping):
            blocked.append(
                RuntimeAction(action_id, "unknown", "blocked", reason="workload_mapping_must_be_object")
            )
            continue

        workload_id = workload.get("workload_id")
        workload_id_value = workload_id if isinstance(workload_id, str) else None
        action_type = workload.get("action_type", SUPPORTED_ACTION)
        if action_type != SUPPORTED_ACTION:
            blocked.append(
                RuntimeAction(
                    action_id,
                    str(action_type),
                    "blocked",
                    workload_id=workload_id_value,
                    role=workload.get("role") if isinstance(workload.get("role"), str) else None,
                    reason="unsupported_action_type",
                )
            )
            continue

        targets = _string_tuple(workload.get("target_tiles"))
        role = workload.get("role")
        reason: str | None = None
        route: Mapping[str, Any] | None = None
        matching_routes = routes_by_workload.get(workload_id_value or "", [])
        if workload_id_value is None:
            reason = "workload_id_must_be_non_empty_string"
        elif not workload_id_value:
            reason = "workload_id_must_be_non_empty_string"
        elif not isinstance(role, str) or role not in allowed_roles or role in blocked_roles:
            reason = "workload_role_not_allowed"
        elif targets is None or not targets:
            reason = "target_tiles_must_be_non_empty_string_list"
        elif len(matching_routes) != 1:
            reason = "exactly_one_route_required_for_workload"
        else:
            route = matching_routes[0]
            route_targets = _string_tuple(route.get("target_tiles"))
            if route.get("route_status") != REQUIRED_ROUTE_STATUS:
                reason = "route_status_must_be_candidate_simulated"
            elif not isinstance(route.get("route_id"), str) or not route.get("route_id"):
                reason = "route_id_must_be_non_empty_string"
            elif route_targets != targets:
                reason = "route_target_tiles_must_match_workload"

        if reason is not None:
            blocked.append(
                RuntimeAction(
                    action_id,
                    SUPPORTED_ACTION,
                    "blocked",
                    workload_id=workload_id_value,
                    role=role if isinstance(role, str) else None,
                    target_tiles=targets or (),
                    route_id=(route.get("route_id") if route and isinstance(route.get("route_id"), str) else None),
                    reason=reason,
                )
            )
            continue

        assert route is not None and targets is not None
        actions.append(
            RuntimeAction(
                action_id,
                SUPPORTED_ACTION,
                "planned",
                workload_id=workload_id_value,
                role=role,
                target_tiles=targets,
                route_id=route["route_id"],
            )
        )

    for field in ("requested_actions", "actions"):
        candidates = profile.get(field, [])
        if not isinstance(candidates, list):
            candidates = [candidates]
        for candidate in candidates:
            action_id = f"ACT_{next_id:03d}"
            next_id += 1
            action_type = candidate.get("action_type") if isinstance(candidate, Mapping) else None
            workload_id = candidate.get("workload_id") if isinstance(candidate, Mapping) else None
            blocked.append(
                RuntimeAction(
                    action_id,
                    str(action_type or "unknown"),
                    "blocked",
                    workload_id=workload_id if isinstance(workload_id, str) else None,
                    reason="unsupported_action_source",
                )
            )

    block_reasons = tuple(
        dict.fromkeys(action.reason for action in blocked if action.reason is not None)
    )
    return RuntimePlan(
        **base,
        plan_status="planned_with_blocks" if blocked else "planned",
        plan_block_reasons=block_reasons,
        actions=tuple(actions),
        blocked_actions=tuple(blocked),
    )
