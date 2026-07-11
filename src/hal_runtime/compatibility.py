"""Informational profile compatibility checks for the current Runtime version."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .models import RUNTIME_VERSION


_REQUIRED_FIELDS = (
    "profile_id",
    "hardware_control_enabled",
    "human_review_required",
    "claim_boundary",
    "voltage_policy",
    "runtime_loader_hint",
    "assigned_workloads",
    "unassigned_workloads",
    "blocked_roles",
    "allowed_roles",
)
_LIST_FIELDS = (
    "assigned_workloads",
    "unassigned_workloads",
    "blocked_roles",
    "allowed_roles",
)
_SUSPICIOUS_ACTION_FIELDS = (
    "runtime_actions",
    "hardware_actions",
    "execution_actions",
    "control_actions",
    "requested_actions",
    "actions",
)


@dataclass(frozen=True)
class CompatibilityResult:
    compatible: bool
    missing_fields: tuple[str, ...] = ()
    unsupported_fields: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    runtime_version: str = RUNTIME_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_version": self.runtime_version,
            "compatible": self.compatible,
            "missing_fields": list(self.missing_fields),
            "unsupported_fields": list(self.unsupported_fields),
            "warnings": list(self.warnings),
        }


def check_compatibility(profile: Mapping[str, Any]) -> CompatibilityResult:
    """Inspect profile shape without mutating it or creating runtime actions."""
    missing = tuple(field for field in _REQUIRED_FIELDS if field not in profile)
    invalid_types = tuple(
        field
        for field in _LIST_FIELDS
        if field in profile and not isinstance(profile[field], list)
    )
    unsupported = tuple(field for field in _SUSPICIOUS_ACTION_FIELDS if field in profile)
    warnings = tuple(
        [f"invalid_field_type:{field}:expected_list" for field in invalid_types]
        + [f"unsupported_action_like_field_detected:{field}" for field in unsupported]
    )
    return CompatibilityResult(
        compatible=not missing and not invalid_types,
        missing_fields=missing,
        unsupported_fields=unsupported,
        warnings=warnings,
    )
