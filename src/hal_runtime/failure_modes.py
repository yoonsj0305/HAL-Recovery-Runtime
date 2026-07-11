"""Fixed failure modes available to the simulation layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .models import RUNTIME_VERSION


@dataclass(frozen=True)
class FailureModeInfo:
    failure_mode: str
    description: str
    rollback_strategy: str

    def to_dict(self) -> dict[str, str]:
        return {
            "failure_mode": self.failure_mode,
            "description": self.description,
            "rollback_strategy": self.rollback_strategy,
        }


FAILURE_MODES = (
    FailureModeInfo("none", "Runs mock simulation without an injected failure.", "none"),
    FailureModeInfo(
        "adapter_unavailable",
        "Simulates a mock adapter becoming unavailable before action simulation.",
        "safe_stop",
    ),
    FailureModeInfo("action_timeout", "Simulates an action timeout.", "safe_stop"),
    FailureModeInfo(
        "route_unavailable",
        "Simulates a candidate route becoming unavailable.",
        "rollback_to_pre_simulation_state",
    ),
    FailureModeInfo(
        "unsupported_role_after_injection",
        "Simulates a role becoming unsupported after validation.",
        "safe_stop",
    ),
    FailureModeInfo(
        "partial_plan_failure",
        "Simulates a later action failing after earlier actions were simulated.",
        "simulated_revert_completed_actions",
    ),
    FailureModeInfo(
        "forced_safety_boundary_failure",
        "Simulates a safety boundary failure before any action.",
        "no_action_taken",
    ),
)


def supported_failure_modes() -> set[str]:
    return {mode.failure_mode for mode in FAILURE_MODES}


def failure_modes_document() -> dict[str, Any]:
    return {
        "runtime_version": RUNTIME_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "failure_modes": [mode.to_dict() for mode in FAILURE_MODES],
    }

