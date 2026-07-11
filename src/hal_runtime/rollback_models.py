"""Simulation-only rollback plan and report models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adapter_models import CLAIM_BOUNDARY, SourcePlanSummary
from .models import RUNTIME_VERSION


ROLLBACK_SIMULATION_VERSION = RUNTIME_VERSION
ROLLBACK_LIMITATIONS = (
    "simulation_only",
    "no_" + "real_" + "rollback",
    "no_hardware_control",
    "not_certified",
)


@dataclass(frozen=True)
class RollbackAction:
    rollback_action_id: str
    rollback_action_type: str
    source_action_id: str | None
    status: str
    simulation_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollback_action_id": self.rollback_action_id,
            "rollback_action_type": self.rollback_action_type,
            "source_action_id": self.source_action_id,
            "status": self.status,
            "simulation_reason": self.simulation_reason,
        }


@dataclass(frozen=True)
class RollbackPlan:
    source_plan_status: str
    scenario_id: str
    failure_mode: str
    rollback_required: bool
    safe_stop_required: bool
    no_action_taken: bool
    rollback_plan_status: str
    rollback_strategy: str
    rollback_actions: tuple[RollbackAction, ...] = ()
    non_reversible_actions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        counts = _action_counts(self.rollback_actions)
        return {
            "runtime_version": RUNTIME_VERSION,
            "rollback_simulation_version": ROLLBACK_SIMULATION_VERSION,
            "simulation_only": True,
            "hardware_control_enabled": False,
            "claim_boundary": CLAIM_BOUNDARY,
            "source_plan_status": self.source_plan_status,
            "scenario_id": self.scenario_id,
            "failure_mode": self.failure_mode,
            "rollback_required": self.rollback_required,
            "safe_stop_required": self.safe_stop_required,
            "no_action_taken": self.no_action_taken,
            **counts,
            "rollback_plan_status": self.rollback_plan_status,
            "rollback_strategy": self.rollback_strategy,
            "rollback_actions": [action.to_dict() for action in self.rollback_actions],
            "non_reversible_actions": list(self.non_reversible_actions),
            "known_limitations": list(ROLLBACK_LIMITATIONS),
        }


@dataclass(frozen=True)
class RollbackReport:
    plan_loaded: bool
    scenario_loaded: bool
    source_plan_summary: SourcePlanSummary
    scenario_summary: dict[str, Any]
    rollback_simulation_status: str
    injected_failure_mode: str
    injected_failure_action_id: str | None
    simulated_actions_before_failure: int
    failed_actions: int
    skipped_actions: int
    rollback_required: bool
    safe_stop_required: bool
    no_action_taken: bool
    rollback_actions_planned: int
    simulated_revert_actions_planned: int
    safe_stop_markers_planned: int
    skip_markers_planned: int
    no_action_markers_planned: int
    rollback_strategy: str
    failure_reasons: tuple[str, ...] = ()
    rollback_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_version": RUNTIME_VERSION,
            "rollback_simulation_version": ROLLBACK_SIMULATION_VERSION,
            "rollback_semantics_version": RUNTIME_VERSION,
            "simulation_only": True,
            "hardware_control_enabled": False,
            "claim_boundary": CLAIM_BOUNDARY,
            "plan_loaded": self.plan_loaded,
            "scenario_loaded": self.scenario_loaded,
            "source_plan_summary": self.source_plan_summary.to_dict(),
            "scenario_summary": self.scenario_summary,
            "rollback_simulation_status": self.rollback_simulation_status,
            "injected_failure_mode": self.injected_failure_mode,
            "injected_failure_action_id": self.injected_failure_action_id,
            "simulated_actions_before_failure": self.simulated_actions_before_failure,
            "failed_actions": self.failed_actions,
            "skipped_actions": self.skipped_actions,
            "rollback_required": self.rollback_required,
            "safe_stop_required": self.safe_stop_required,
            "no_action_taken": self.no_action_taken,
            "rollback_actions_planned": self.rollback_actions_planned,
            "simulated_revert_actions_planned": self.simulated_revert_actions_planned,
            "safe_stop_markers_planned": self.safe_stop_markers_planned,
            "skip_markers_planned": self.skip_markers_planned,
            "no_action_markers_planned": self.no_action_markers_planned,
            "rollback_strategy": self.rollback_strategy,
            "failure_reasons": list(self.failure_reasons),
            "rollback_reasons": list(self.rollback_reasons),
            "known_limitations": list(ROLLBACK_LIMITATIONS),
        }


@dataclass(frozen=True)
class FailureSimulationOutcome:
    rollback_plan: RollbackPlan
    rollback_report: RollbackReport
    trace_events: tuple[dict[str, Any], ...]


def _action_counts(actions: tuple[RollbackAction, ...]) -> dict[str, int]:
    return {
        "simulated_revert_actions_planned": sum(
            action.rollback_action_type == "simulated_revert" for action in actions
        ),
        "safe_stop_markers_planned": sum(
            action.rollback_action_type == "safe_stop_marker" for action in actions
        ),
        "skip_markers_planned": sum(
            action.rollback_action_type == "skip_marker" for action in actions
        ),
        "no_action_markers_planned": sum(
            action.rollback_action_type == "no_action_marker" for action in actions
        ),
    }
