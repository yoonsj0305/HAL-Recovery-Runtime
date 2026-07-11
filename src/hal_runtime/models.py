"""Dependency-free runtime data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


RUNTIME_VERSION = "1.0.0"


@dataclass(frozen=True)
class SafetyGateResult:
    passed: bool
    failure_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    degraded_mode: bool = False


@dataclass(frozen=True)
class RuntimeAction:
    action_id: str
    action_type: str
    status: str
    workload_id: str | None = None
    role: str | None = None
    target_tiles: tuple[str, ...] = ()
    route_id: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "status": self.status,
        }
        if self.workload_id is not None:
            result["workload_id"] = self.workload_id
        if self.role is not None:
            result["role"] = self.role
        if self.target_tiles:
            result["target_tiles"] = list(self.target_tiles)
        if self.route_id is not None:
            result["route_id"] = self.route_id
        if self.reason is not None:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True)
class RuntimePlan:
    profile_id: str
    hardware_control_enabled: bool
    human_review_required: bool
    claim_boundary: str | None
    plan_status: str = "planned"
    plan_block_reasons: tuple[str, ...] = ()
    actions: tuple[RuntimeAction, ...] = ()
    blocked_actions: tuple[RuntimeAction, ...] = ()
    execution_mode: str = "dry_run"
    runtime_version: str = RUNTIME_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_version": self.runtime_version,
            "profile_id": self.profile_id,
            "execution_mode": self.execution_mode,
            "hardware_control_enabled": self.hardware_control_enabled,
            "human_review_required": self.human_review_required,
            "claim_boundary": self.claim_boundary,
            "plan_status": self.plan_status,
            "plan_block_reasons": list(self.plan_block_reasons),
            "actions": [action.to_dict() for action in self.actions],
            "blocked_actions": [action.to_dict() for action in self.blocked_actions],
        }


@dataclass(frozen=True)
class RuntimeReport:
    profile_loaded: bool
    safety_gate_passed: bool
    planned_actions: int
    blocked_actions: int
    degraded_mode_entered: bool
    runtime_status: str
    hardware_control_enabled: bool
    human_review_required: bool
    claim_boundary: str | None
    safety_gate_evaluated: bool = True
    bundle_gate_evaluated: bool = False
    execution_gate_stage: str = "dry_run_completed"
    safety_failure_reasons: tuple[str, ...] = ()
    degraded_mode_reasons: tuple[str, ...] = ()
    bundle_mode: bool = False
    bundle_validation_passed: bool | None = None
    bundle_validation_status: str | None = None
    bundle_validation_reasons: tuple[str, ...] = ()
    bundle_validation_warnings: tuple[str, ...] = ()
    present_artifacts: tuple[str, ...] = ()
    missing_artifacts: tuple[str, ...] = ()
    degraded_bundle_mode: bool = False
    supporting_artifact_count: int = 0
    blocked_action_details: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    execution_mode: str = "dry_run"
    runtime_version: str = RUNTIME_VERSION

    def to_dict(self) -> dict[str, Any]:
        result = {
            "runtime_version": self.runtime_version,
            "execution_mode": self.execution_mode,
            "profile_loaded": self.profile_loaded,
            "safety_gate_evaluated": self.safety_gate_evaluated,
            "safety_gate_passed": self.safety_gate_passed,
            "bundle_gate_evaluated": self.bundle_gate_evaluated,
            "execution_gate_stage": self.execution_gate_stage,
            "planned_actions": self.planned_actions,
            "blocked_actions": self.blocked_actions,
            "degraded_mode_entered": self.degraded_mode_entered,
            "runtime_status": self.runtime_status,
            "hardware_control_enabled": self.hardware_control_enabled,
            "human_review_required": self.human_review_required,
            "claim_boundary": self.claim_boundary,
            "safety_failure_reasons": list(self.safety_failure_reasons),
            "degraded_mode_reasons": list(self.degraded_mode_reasons),
            "bundle_mode": self.bundle_mode,
        }
        if self.bundle_mode:
            result.update(
                {
                    "bundle_validation_passed": self.bundle_validation_passed,
                    "bundle_validation_status": self.bundle_validation_status,
                    "bundle_validation_reasons": list(self.bundle_validation_reasons),
                    "bundle_validation_warnings": list(self.bundle_validation_warnings),
                    "present_artifacts": list(self.present_artifacts),
                    "missing_artifacts": list(self.missing_artifacts),
                    "degraded_bundle_mode": self.degraded_bundle_mode,
                    "supporting_artifact_count": self.supporting_artifact_count,
                }
            )
        if self.blocked_action_details:
            result["blocked_action_details"] = list(self.blocked_action_details)
        return result


@dataclass(frozen=True)
class DryRunResult:
    plan: RuntimePlan
    report: RuntimeReport
    events: tuple[dict[str, Any], ...]
