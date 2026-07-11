"""Fail-closed validation for simulation-only profiles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import SafetyGateResult


_EXACT_SAFETY_REQUIREMENTS: tuple[tuple[str, Any, str], ...] = (
    (
        "hardware_control_enabled",
        False,
        "hardware_control_enabled_must_be_false",
    ),
    ("human_review_required", True, "human_review_required_must_be_true"),
    (
        "claim_boundary",
        "simulation_only_not_certified",
        "claim_boundary_must_be_simulation_only_not_certified",
    ),
    ("voltage_policy", "no_hardware_control", "voltage_policy_must_be_no_hardware_control"),
    ("runtime_loader_hint", "simulation_only", "runtime_loader_hint_must_be_simulation_only"),
)

_REQUIRED_LIST_FIELDS = (
    "assigned_workloads",
    "unassigned_workloads",
    "blocked_roles",
    "allowed_roles",
)


class SafetyGate:
    """Validate immutable safety and planning boundaries."""

    def evaluate(self, profile: Mapping[str, Any]) -> SafetyGateResult:
        failures: list[str] = []
        warnings: list[str] = []

        for field, expected, reason in _EXACT_SAFETY_REQUIREMENTS:
            actual = profile.get(field)
            exact_match = (
                actual is expected
                if isinstance(expected, bool)
                else isinstance(actual, str) and actual == expected
            )
            if not exact_match:
                failures.append(reason)

        if not isinstance(profile.get("profile_id"), str) or not profile.get("profile_id"):
            failures.append("profile_id_must_be_non_empty_string")

        for field in _REQUIRED_LIST_FIELDS:
            if field not in profile:
                failures.append(
                    "missing_unassigned_workloads"
                    if field == "unassigned_workloads"
                    else f"{field}_is_required"
                )
            elif not isinstance(profile[field], list):
                failures.append(
                    "unassigned_workloads_must_be_list"
                    if field == "unassigned_workloads"
                    else f"{field}_must_be_list"
                )
            elif field in {"blocked_roles", "allowed_roles"} and not all(
                isinstance(item, str) for item in profile[field]
            ):
                failures.append(f"{field}_must_be_string_list")

        degraded = "preferred_routes" not in profile
        if degraded:
            warnings.append("preferred_routes_missing")
        elif not isinstance(profile["preferred_routes"], list):
            failures.append("preferred_routes_must_be_list")

        return SafetyGateResult(
            passed=not failures,
            failure_reasons=tuple(failures),
            warnings=tuple(warnings),
            degraded_mode=degraded and not failures,
        )


def evaluate_profile(profile: Mapping[str, Any]) -> SafetyGateResult:
    return SafetyGate().evaluate(profile)
