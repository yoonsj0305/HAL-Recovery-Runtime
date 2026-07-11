"""Data models for the simulation-only mock adapter layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import RUNTIME_VERSION


CLAIM_BOUNDARY = "simulation_only_not_certified"
ADAPTER_LAYER_VERSION = RUNTIME_VERSION
KNOWN_LIMITATIONS = (
    "mock_adapter_only",
    "no_real_hardware_control",
    "no_firmware_or_driver_integration",
    "simulation_only_not_certified",
)


@dataclass(frozen=True)
class MockAdapterInfo:
    adapter_id: str
    adapter_type: str
    supported_action_types: tuple[str, ...]
    supported_roles: tuple[str, ...]
    simulation_only: bool = True
    hardware_control_enabled: bool = False
    claim_boundary: str = CLAIM_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_type": self.adapter_type,
            "supported_action_types": list(self.supported_action_types),
            "supported_roles": list(self.supported_roles),
            "simulation_only": self.simulation_only,
            "hardware_control_enabled": self.hardware_control_enabled,
            "claim_boundary": self.claim_boundary,
        }


@dataclass(frozen=True)
class MockAdapterResult:
    adapter_id: str
    action_id: str
    action_type: str
    workload_id: str | None
    simulation_status: str
    simulation_reason: str
    hardware_control_enabled: bool = False
    claim_boundary: str = CLAIM_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "workload_id": self.workload_id,
            "simulation_status": self.simulation_status,
            "simulation_reason": self.simulation_reason,
            "hardware_control_enabled": self.hardware_control_enabled,
            "claim_boundary": self.claim_boundary,
        }


@dataclass(frozen=True)
class PlanValidationResult:
    structurally_valid: bool
    safety_boundary_passed: bool
    validation_reasons: tuple[str, ...] = ()
    safety_failure_reasons: tuple[str, ...] = ()

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.validation_reasons + self.safety_failure_reasons


@dataclass(frozen=True)
class SourcePlanSummary:
    runtime_version: str | None
    profile_id: str | None
    execution_mode: str | None
    plan_status: str | None
    planned_action_count: int
    blocked_action_count: int
    plan_block_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_version": self.runtime_version,
            "profile_id": self.profile_id,
            "execution_mode": self.execution_mode,
            "plan_status": self.plan_status,
            "planned_action_count": self.planned_action_count,
            "blocked_action_count": self.blocked_action_count,
            "plan_block_reasons": list(self.plan_block_reasons),
        }


@dataclass(frozen=True)
class AdapterResultSummary:
    simulated: int = 0
    blocked_unsupported_action: int = 0
    blocked_unsupported_role: int = 0
    blocked_safety_boundary: int = 0
    skipped_plan_not_executable: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "simulated": self.simulated,
            "blocked_unsupported_action": self.blocked_unsupported_action,
            "blocked_unsupported_role": self.blocked_unsupported_role,
            "blocked_safety_boundary": self.blocked_safety_boundary,
            "skipped_plan_not_executable": self.skipped_plan_not_executable,
        }


@dataclass(frozen=True)
class AdapterSimulationReport:
    plan_loaded: bool
    plan_status: str
    adapter_simulation_status: str
    available_adapters: int
    simulated_actions: int
    blocked_actions: int
    skipped_actions: int
    adapter_execution_stage: str
    source_plan_summary: SourcePlanSummary
    adapter_result_summary: AdapterResultSummary
    adapter_block_reasons: tuple[str, ...] = ()
    adapter_safety_failure_reasons: tuple[str, ...] = ()
    adapter_validation_reasons: tuple[str, ...] = ()
    adapter_results: tuple[MockAdapterResult, ...] = ()
    known_limitations: tuple[str, ...] = KNOWN_LIMITATIONS
    runtime_version: str = RUNTIME_VERSION
    adapter_layer_version: str = ADAPTER_LAYER_VERSION
    simulation_only: bool = True
    hardware_control_enabled: bool = False
    claim_boundary: str = CLAIM_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_version": self.runtime_version,
            "adapter_layer_version": self.adapter_layer_version,
            "simulation_only": self.simulation_only,
            "hardware_control_enabled": self.hardware_control_enabled,
            "claim_boundary": self.claim_boundary,
            "plan_loaded": self.plan_loaded,
            "plan_status": self.plan_status,
            "adapter_simulation_status": self.adapter_simulation_status,
            "available_adapters": self.available_adapters,
            "simulated_actions": self.simulated_actions,
            "blocked_actions": self.blocked_actions,
            "skipped_actions": self.skipped_actions,
            "adapter_execution_stage": self.adapter_execution_stage,
            "adapter_block_reasons": list(self.adapter_block_reasons),
            "adapter_safety_failure_reasons": list(
                self.adapter_safety_failure_reasons
            ),
            "adapter_validation_reasons": list(self.adapter_validation_reasons),
            "source_plan_summary": self.source_plan_summary.to_dict(),
            "adapter_result_summary": self.adapter_result_summary.to_dict(),
            "adapter_results": [result.to_dict() for result in self.adapter_results],
            "known_limitations": list(self.known_limitations),
        }


@dataclass(frozen=True)
class AdapterSimulationOutcome:
    report: AdapterSimulationReport
    trace_events: tuple[dict[str, Any], ...]
