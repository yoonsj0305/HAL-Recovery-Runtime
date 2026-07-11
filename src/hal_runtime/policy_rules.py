"""Fixed built-in rules for policy simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .models import RUNTIME_VERSION


@dataclass(frozen=True)
class PolicyModeInfo:
    policy_mode: str
    description: str
    real_execution_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_mode": self.policy_mode,
            "description": self.description,
            "real_execution_allowed": self.real_execution_allowed,
        }


POLICY_MODES = (
    PolicyModeInfo(
        "conservative_default",
        "Default simulation-only policy that favors blocking or human review over action.",
    ),
    PolicyModeInfo(
        "safe_stop_first",
        "Prioritizes a simulated safe-stop marker when failure or uncertainty exists.",
    ),
    PolicyModeInfo(
        "rollback_if_prior_actions",
        "Selects simulated rollback only when prior simulated actions exist.",
    ),
    PolicyModeInfo(
        "no_retry_v0_5_0",
        "Forbids retry selection in Runtime v0.5.0.",
    ),
    PolicyModeInfo(
        "degraded_requires_review",
        "Routes degraded plans or bundles to human review.",
    ),
    PolicyModeInfo(
        "no_action_on_boundary_failure",
        "Selects no action when any safety boundary fails.",
    ),
)


def supported_policy_modes() -> frozenset[str]:
    return frozenset(mode.policy_mode for mode in POLICY_MODES)


def policy_modes_document() -> dict[str, Any]:
    return {
        "runtime_version": RUNTIME_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "policy_modes": [mode.to_dict() for mode in POLICY_MODES],
    }
